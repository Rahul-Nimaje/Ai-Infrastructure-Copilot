import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventLogEntry


async def list_events_for_server(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    server_id: uuid.UUID,
    level: str | None = None,
    limit: int = 100,
) -> list[EventLogEntry]:
    query = select(EventLogEntry).where(
        EventLogEntry.organization_id == organization_id, EventLogEntry.server_id == server_id
    )
    if level:
        query = query.where(EventLogEntry.level == level)
    query = query.order_by(EventLogEntry.occurred_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
