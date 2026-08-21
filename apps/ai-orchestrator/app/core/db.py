"""Read-only DB access for context-gathering (Planner's inventory lookup,
Windows Agent's event_log_entries reads, conversation history). All writes
(Scripts/Tasks/AuditLogs) happen inside apps/api — see plan simplification
notes in app/graph.py.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
