import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vault import decrypt_secret, encrypt_secret
from app.models.credential import Credential


async def create_credential(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    name: str,
    credential_type: str,
    username: str,
    secret: str,
) -> Credential:
    vault_path = encrypt_secret({"username": username, "secret": secret})
    credential = Credential(
        organization_id=organization_id,
        name=name,
        credential_type=credential_type,
        vault_engine="local_encrypted",
        vault_path=vault_path,
        encrypted_metadata={"username": username},
        created_by_user_id=created_by_user_id,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return credential


async def list_credentials(db: AsyncSession, *, organization_id: uuid.UUID) -> list[Credential]:
    result = await db.execute(
        select(Credential).where(Credential.organization_id == organization_id, Credential.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def resolve_credential_secret(db: AsyncSession, *, organization_id: uuid.UUID, credential_id: uuid.UUID) -> dict:
    """Just-in-time secret resolution — the decrypted material is only ever
    held in memory for the duration of the caller's connection attempt, never
    persisted or logged. Real Vault deployments replace this function's body
    with a Vault Transit/KV read; callers (execution runner, event-log sync)
    are unaffected."""
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id, Credential.organization_id == organization_id)
    )
    credential = result.scalar_one()
    return decrypt_secret(credential.vault_path)


async def delete_credential(db: AsyncSession, *, organization_id: uuid.UUID, credential_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id, Credential.organization_id == organization_id, Credential.deleted_at.is_(None))
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return False
    from datetime import datetime
    cred.deleted_at = datetime.utcnow()
    await db.commit()
    return True

