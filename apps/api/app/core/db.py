from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Plain session dependency, used by endpoints that don't need org scoping
    (e.g. registration, which creates the first organization)."""
    async with SessionLocal() as session:
        yield session


async def get_scoped_db(org_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Sets app.current_org_id for the session's transaction so Postgres RLS
    (docs/04-database-design.md Section 2) enforces tenant isolation as a
    defense-in-depth backstop behind the application-layer org_id filtering
    every repository call already does."""
    async with SessionLocal() as session:
        # Postgres's SET/SET LOCAL statements don't accept bind parameters
        # (`SET LOCAL x = $1` is a syntax error) — set_config() is the
        # parameterized equivalent; its third argument (true) scopes the
        # setting to the current transaction, same as SET LOCAL.
        await session.execute(text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": org_id})
        yield session
