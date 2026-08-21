from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

_hasher = PasswordHasher()
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


@dataclass
class AccessTokenClaims:
    user_id: str
    organization_id: str
    email: str
    permissions: list[str]


def issue_access_token(claims: AccessTokenClaims) -> str:
    now = int(time.time())
    payload = {
        "sub": claims.user_id,
        "org_id": claims.organization_id,
        "email": claims.email,
        "permissions": claims.permissions,
        "iat": now,
        "exp": now + settings.jwt_access_token_ttl_seconds,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def generate_refresh_secret() -> str:
    """The client-visible refresh token is `{row_id}.{this secret}` (assembled
    in app/modules/authentication/service.py once the DB row id is known), so
    a refresh request can look up its row by id before verifying the hash."""
    return uuid.uuid4().hex + uuid.uuid4().hex


def decode_access_token(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Access token has expired."},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Invalid access token."},
        )
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "UNAUTHENTICATED"})
    return AccessTokenClaims(
        user_id=payload["sub"],
        organization_id=payload["org_id"],
        email=payload["email"],
        permissions=payload.get("permissions", []),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AccessTokenClaims:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "UNAUTHENTICATED"})
    return decode_access_token(credentials.credentials)


def require_permission(permission_code: str):
    """FastAPI dependency factory enforcing RBAC per docs/04-database-design.md
    Section 5.4 permission codes (e.g. 'scripts.execute', 'tasks.approve')."""

    async def _check(user: AccessTokenClaims = Depends(get_current_user)) -> AccessTokenClaims:
        if permission_code not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": f"Missing permission: {permission_code}"},
            )
        return user

    return _check
