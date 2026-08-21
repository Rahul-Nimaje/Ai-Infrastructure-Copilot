import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def _sanitize_json(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_sanitize_json(v) for v in data]
    elif isinstance(data, uuid.UUID):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    return data


async def write_audit_log(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_type: str,
    action: str,
    resource_type: str,
    actor_user_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> AuditLog:
    """Every mutating action writes here — docs/04-database-design.md Section
    5.18. Append-only: callers must never UPDATE or DELETE the returned row."""
    entry = AuditLog(
        organization_id=organization_id,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_state=_sanitize_json(before_state) if before_state is not None else None,
        after_state=_sanitize_json(after_state) if after_state is not None else None,
    )
    db.add(entry)
    await db.flush()
    return entry
