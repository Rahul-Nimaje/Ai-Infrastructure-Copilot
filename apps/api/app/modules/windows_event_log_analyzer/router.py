import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import require_permission
from app.core.winrm_client import WinRmTarget, run_powershell
from app.dependencies import get_org_db
from app.modules.credentials.service import resolve_credential_secret
from app.modules.infrastructure_inventory.service import get_server
from app.modules.windows_event_log_analyzer import service
from app.modules.windows_event_log_analyzer.schemas import EventLogEntryOut

router = APIRouter(prefix="/api/v1/servers/{server_id}/events", tags=["windows-event-log-analyzer"])

# Real Get-WinEvent output would be parsed properly; this is intentionally the
# minimal read-only command used when EXECUTION_ENABLED=true, per plan
# simplification #6 (no separate MCP server process yet, same tool boundary).
_GET_RECENT_EVENTS_SCRIPT = (
    "Get-WinEvent -LogName System,Application,Security -MaxEvents 50 "
    "| Select-Object Id, LevelDisplayName, ProviderName, Message, TimeCreated "
    "| ConvertTo-Json"
)


@router.get("", response_model=None)
async def list_events(
    server_id: uuid.UUID,
    level: str | None = None,
    user=Depends(require_permission("events.read")),
    db: AsyncSession = Depends(get_org_db),
):
    entries = await service.list_events_for_server(
        db, organization_id=uuid.UUID(user.organization_id), server_id=server_id, level=level,
    )
    return {"data": [EventLogEntryOut.model_validate(e) for e in entries]}


@router.post("/sync", response_model=None)
async def sync_events(
    server_id: uuid.UUID,
    user=Depends(require_permission("events.read")),
    db: AsyncSession = Depends(get_org_db),
):
    """Read-only diagnostic — auto-runs without Human Approval per the global
    execution safety rule (docs/03-LLD.md Module 5 Safety notes). When
    EXECUTION_ENABLED=false this is a no-op that tells the caller to rely on
    seeded fixture data, matching plan simplification #3/#6."""
    if not settings.execution_enabled:
        return {
            "data": {
                "synced": False,
                "reason": "EXECUTION_ENABLED=false; using seeded event_log_entries fixture data.",
            }
        }

    server = await get_server(db, organization_id=uuid.UUID(user.organization_id), server_id=server_id)
    if server is None or server.credential_id is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "VALIDATION_ERROR", "message": "Server not found or has no credential configured."},
        )
    secret = await resolve_credential_secret(
        db, organization_id=uuid.UUID(user.organization_id), credential_id=server.credential_id
    )
    target = WinRmTarget(
        host=server.hostname, username=secret["username"], password=secret["secret"],
        port=server.winrm_port, ssl=server.winrm_use_ssl,
    )
    stdout, stderr, rc = await run_in_threadpool(run_powershell, target, _GET_RECENT_EVENTS_SCRIPT)
    if rc != 0:
        raise HTTPException(status_code=502, detail={"code": "INTERNAL_ERROR", "message": stderr or "WinRM sync failed."})
    return {"data": {"synced": True, "raw_output": stdout}}
