import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_permission
from app.dependencies import get_org_db
from app.modules.infrastructure_inventory import discovery, service
from app.modules.infrastructure_inventory.schemas import RegisterServerRequest, ServerOut

router = APIRouter(prefix="/api/v1", tags=["infrastructure-inventory"])


@router.get("/servers", response_model=None)
async def list_servers(
    user=Depends(require_permission("servers.read")),
    db: AsyncSession = Depends(get_org_db),
):
    servers = await service.list_servers(db, organization_id=uuid.UUID(user.organization_id))
    return {"data": [ServerOut.model_validate(s) for s in servers]}


@router.get("/servers/{server_id}", response_model=None)
async def get_server(
    server_id: uuid.UUID,
    user=Depends(require_permission("servers.read")),
    db: AsyncSession = Depends(get_org_db),
):
    server = await service.get_server(db, organization_id=uuid.UUID(user.organization_id), server_id=server_id)
    if server is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Server not found."})
    return {"data": ServerOut.model_validate(server)}


@router.post("/servers", status_code=status.HTTP_201_CREATED, response_model=None)
async def register_server(
    payload: RegisterServerRequest,
    user=Depends(require_permission("servers.write")),
    db: AsyncSession = Depends(get_org_db),
):
    server = await service.register_server(
        db,
        organization_id=uuid.UUID(user.organization_id),
        hostname=payload.hostname,
        ip_address=payload.ip_address,
        os_type=payload.os_type,
        os_version=payload.os_version,
        environment=payload.environment,
        credential_id=payload.credential_id,
        winrm_port=payload.winrm_port,
        winrm_use_ssl=payload.winrm_use_ssl,
    )
    return {"data": ServerOut.model_validate(server)}


@router.delete("/servers/{server_id}", response_model=None)
async def detach_server(
    server_id: uuid.UUID,
    user=Depends(require_permission("servers.write")),
    db: AsyncSession = Depends(get_org_db),
):
    server = await service.detach_server(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id), server_id=server_id
    )
    if server is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Server not found."})
    return {"data": {"id": str(server_id), "detached": True}}


class ScanNetworkRequest(BaseModel):
    cidr: str  # e.g. "10.20.4.0/24" — explicit range only, never guessed


@router.post("/inventory/scan", response_model=None)
async def scan_network(
    payload: ScanNetworkRequest,
    user=Depends(require_permission("servers.read")),
):
    """Read-only — auto-runs without Human Approval per docs/03-LLD.md
    Module 2 Safety notes. Returns candidates only; nothing is persisted
    until the caller registers one via POST /servers."""
    candidates = await discovery.scan_network(payload.cidr)
    return {"data": candidates}
