from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta

import jwt
import pyotp
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.security import (
    AccessTokenClaims,
    generate_refresh_secret,
    hash_password,
    issue_access_token,
    verify_password,
)

_refresh_hasher = PasswordHasher()
from app.core.vault import decrypt_secret, encrypt_secret
from app.models.organization import Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import RefreshToken, User

# Seeded once per organization at registration time. Phase 1 ships a single
# "Admin" system role with every permission the 5 in-scope modules need;
# per-module granularity (Server Operator, Auditor, etc.) is Phase 2+.
PHASE_1_PERMISSIONS = [
    ("servers.read", "Infrastructure Inventory"),
    ("servers.write", "Infrastructure Inventory"),
    ("events.read", "Windows Event Log Analyzer"),
    ("scripts.read", "PowerShell Generator"),
    ("scripts.write", "PowerShell Generator"),
    ("scripts.execute", "PowerShell Generator"),
    ("tasks.read", "PowerShell Generator"),
    ("tasks.approve", "PowerShell Generator"),
    ("ai_chat.use", "AI Chat"),
]


async def _ensure_global_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission))
    existing = {p.code: p for p in result.scalars().all()}
    created = []
    for code, module in PHASE_1_PERMISSIONS:
        if code not in existing:
            perm = Permission(code=code, module=module)
            db.add(perm)
            created.append(perm)
    if created:
        await db.flush()
    result = await db.execute(select(Permission))
    return list(result.scalars().all())


async def register_organization_and_admin(
    db: AsyncSession, *, organization_name: str, email: str, password: str, full_name: str
) -> User:
    slug = organization_name.lower().replace(" ", "-")[:100]
    org = Organization(name=organization_name, slug=slug, status="active")
    db.add(org)
    await db.flush()

    permissions = await _ensure_global_permissions(db)

    admin_role = Role(organization_id=org.id, name="Admin", is_system_role=True)
    db.add(admin_role)
    await db.flush()
    for perm in permissions:
        db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

    user = User(
        organization_id=org.id,
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db.commit()
    return user


async def _get_user_permissions(db: AsyncSession, user: User) -> list[str]:
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    )
    return [row[0] for row in result.all()]


async def get_user_role_names(db: AsyncSession, user: User) -> list[str]:
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    )
    return [row[0] for row in result.all()]


def _issue_mfa_challenge(user_id: uuid.UUID) -> str:
    now = int(time.time())
    payload = {"sub": str(user_id), "type": "mfa_challenge", "iat": now, "exp": now + 300}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode_mfa_challenge(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Invalid or expired MFA challenge."})
    if payload.get("type") != "mfa_challenge":
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR"})
    return uuid.UUID(payload["sub"])


async def _issue_token_pair(
    db: AsyncSession, user: User, *, family_id: uuid.UUID | None = None
) -> tuple[str, str]:
    """Issues an access token plus a new refresh-token row. `family_id` is
    passed on rotation (see refresh_tokens below) so reuse of an already-
    rotated token can revoke the whole lineage, not just the one row —
    docs/05-api-design.md Section 2 refresh-token flow, step 3."""
    permissions = await _get_user_permissions(db, user)
    access_token = issue_access_token(
        AccessTokenClaims(
            user_id=str(user.id), organization_id=str(user.organization_id), email=user.email, permissions=permissions
        )
    )
    row_id = uuid.uuid4()
    secret = generate_refresh_secret()
    token_row = RefreshToken(
        id=row_id,
        user_id=user.id,
        token_hash=_refresh_hasher.hash(secret),
        family_id=family_id or uuid.uuid4(),
        expires_at=datetime.utcnow() + timedelta(seconds=settings.jwt_refresh_token_ttl_seconds),
    )
    db.add(token_row)
    await db.commit()
    raw_refresh = f"{row_id}.{secret}"
    return access_token, raw_refresh


async def refresh_tokens(db: AsyncSession, *, raw_refresh_token: str):
    """Rotates a refresh token. Reuse of an already-revoked token is treated
    as a token-theft signal: the entire family is revoked and the caller must
    re-authenticate — docs/05-api-design.md Section 2, step 3."""
    try:
        row_id_str, secret = raw_refresh_token.split(".", 1)
        row_id = uuid.UUID(row_id_str)
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Malformed refresh token."})

    result = await db.execute(select(RefreshToken).where(RefreshToken.id == row_id))
    token_row = result.scalar_one_or_none()
    if token_row is None or token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Refresh token not found or expired."})

    try:
        _refresh_hasher.verify(token_row.token_hash, secret)
    except VerifyMismatchError:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Invalid refresh token."})

    if token_row.revoked:
        # Reuse of a rotated-out token: revoke the whole family, force re-login.
        await db.execute(
            update(RefreshToken).where(RefreshToken.family_id == token_row.family_id).values(revoked=True)
        )
        await db.commit()
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHENTICATED", "message": "Refresh token reuse detected; please log in again."},
        )

    token_row.revoked = True
    result = await db.execute(select(User).where(User.id == token_row.user_id))
    user = result.scalar_one()
    access_token, raw_refresh = await _issue_token_pair(db, user, family_id=token_row.family_id)
    return {"access_token": access_token, "refresh_token": raw_refresh, "expires_in": settings.jwt_access_token_ttl_seconds}


async def logout(db: AsyncSession, *, raw_refresh_token: str) -> None:
    try:
        row_id_str, _secret = raw_refresh_token.split(".", 1)
        row_id = uuid.UUID(row_id_str)
    except (ValueError, IndexError):
        return
    result = await db.execute(select(RefreshToken).where(RefreshToken.id == row_id))
    token_row = result.scalar_one_or_none()
    if token_row is not None:
        token_row.revoked = True
        await db.commit()


async def authenticate(db: AsyncSession, *, email: str, password: str):
    result = await db.execute(select(User).where(User.email == email.lower(), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Invalid email or password."})
    if user.status != "active":
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "User is not active."})

    if user.mfa_enabled:
        return {"mfa_required": True, "mfa_challenge_id": _issue_mfa_challenge(user.id)}

    access_token, refresh_token = await _issue_token_pair(db, user)
    roles = await get_user_role_names(db, user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.jwt_access_token_ttl_seconds,
        "user": user,
        "roles": roles,
    }


async def verify_mfa(db: AsyncSession, *, mfa_challenge_id: str, code: str):
    user_id = _decode_mfa_challenge(mfa_challenge_id)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.mfa_secret_ref:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "MFA is not enrolled for this user."})

    secret = decrypt_secret(user.mfa_secret_ref)["secret"]
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Invalid MFA code."})

    user.last_login_at = datetime.utcnow()
    access_token, refresh_token = await _issue_token_pair(db, user)
    roles = await get_user_role_names(db, user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.jwt_access_token_ttl_seconds,
        "user": user,
        "roles": roles,
    }


async def enroll_mfa(db: AsyncSession, *, user: User) -> tuple[str, str]:
    secret = pyotp.random_base32()
    user.mfa_secret_ref = encrypt_secret({"secret": secret})
    await db.commit()
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="AI Infrastructure Copilot")
    return provisioning_uri, secret


async def confirm_mfa_enrollment(db: AsyncSession, *, user: User, code: str) -> None:
    if not user.mfa_secret_ref:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": "Call /auth/mfa/enable first."})
    secret = decrypt_secret(user.mfa_secret_ref)["secret"]
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHENTICATED", "message": "Invalid MFA code."})
    user.mfa_enabled = True
    await db.commit()
