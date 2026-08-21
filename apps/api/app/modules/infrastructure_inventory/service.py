import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.infrastructure import InfrastructureInventory, Server


async def list_servers(db: AsyncSession, *, organization_id: uuid.UUID) -> list[Server]:
    result = await db.execute(
        select(Server).where(Server.organization_id == organization_id, Server.deleted_at.is_(None))
        .order_by(Server.hostname)
    )
    return list(result.scalars().all())


async def get_server(db: AsyncSession, *, organization_id: uuid.UUID, server_id: uuid.UUID) -> Server | None:
    result = await db.execute(
        select(Server).where(Server.id == server_id, Server.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def register_server(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    hostname: str,
    ip_address: str | None,
    os_type: str,
    os_version: str | None,
    environment: str,
    credential_id: uuid.UUID | None,
    winrm_port: int = 5986,
    winrm_use_ssl: bool = True,
) -> Server:
    server = Server(
        organization_id=organization_id,
        hostname=hostname,
        ip_address=ip_address,
        os_type=os_type,
        os_version=os_version,
        environment=environment,
        credential_id=credential_id,
        winrm_port=winrm_port,
        winrm_use_ssl=winrm_use_ssl,
    )
    db.add(server)
    await db.flush()
    db.add(
        InfrastructureInventory(
            organization_id=organization_id,
            asset_type="server",
            asset_id=server.id,
            discovered_via="manual",
            attributes={"hostname": hostname, "os_type": os_type},
        )
    )
    await db.commit()
    await db.refresh(server)
    return server


async def detach_server(db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, server_id: uuid.UUID) -> Server | None:
    """Soft-deletes the server (docs/04-database-design.md Section 3: servers
    are soft-deleted, referenced by history/audit). The InfrastructureInventory
    row is hard-deleted since that table only ever tracks *current* assets."""
    server = await get_server(db, organization_id=organization_id, server_id=server_id)
    if server is None or server.deleted_at is not None:
        return None

    server.deleted_at = datetime.utcnow()
    await db.execute(
        delete(InfrastructureInventory).where(
            InfrastructureInventory.organization_id == organization_id,
            InfrastructureInventory.asset_type == "server",
            InfrastructureInventory.asset_id == server_id,
        )
    )
    await write_audit_log(
        db, organization_id=organization_id, actor_type="user", actor_user_id=user_id,
        action="server.detach", resource_type="server", resource_id=server_id,
        before_state={"deleted_at": None}, after_state={"deleted_at": server.deleted_at.isoformat()},
    )
    await db.commit()
    return server
