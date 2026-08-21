from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_scoped_db
from app.core.security import AccessTokenClaims, get_current_user


async def get_org_db(
    user: AccessTokenClaims = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """Org-scoped DB session dependency for every authenticated endpoint —
    org_id always comes from the JWT, never a client-supplied parameter,
    per docs/05-api-design.md Section 1."""
    async for session in get_scoped_db(user.organization_id):
        yield session
