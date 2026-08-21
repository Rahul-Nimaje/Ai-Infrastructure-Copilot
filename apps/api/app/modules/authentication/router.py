import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import AccessTokenClaims, get_current_user
from app.dependencies import get_org_db
from app.modules.authentication import service
from app.modules.authentication.schemas import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    MfaConfirmRequest,
    MfaEnableResponse,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    UserOut,
)
from app.models.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _user_out(user: User, roles: list[str]) -> UserOut:
    return UserOut(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        status=user.status,
        roles=roles,
        employee_id=user.employee_id,
        phone_number=user.phone_number,
        department=user.department,
        designation=user.designation,
        profile_picture=user.profile_picture,
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register_organization_and_admin(
        db, organization_name=payload.organization_name, email=payload.email,
        password=payload.password, full_name=payload.full_name,
    )
    return {"data": {"id": str(user.id), "organization_id": str(user.organization_id), "email": user.email}}


@router.post("/login", response_model=None)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await service.authenticate(db, email=payload.email, password=payload.password)
    if result.get("mfa_required"):
        return {"data": LoginResponse(mfa_required=True, mfa_challenge_id=result["mfa_challenge_id"])}
    return {
        "data": LoginResponse(
            access_token=result["access_token"], refresh_token=result["refresh_token"],
            expires_in=result["expires_in"], user=_user_out(result["user"], result["roles"]),
        )
    }


@router.post("/mfa/verify")
async def mfa_verify(payload: MfaVerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await service.verify_mfa(db, mfa_challenge_id=payload.mfa_challenge_id, code=payload.code)
    return {
        "data": LoginResponse(
            access_token=result["access_token"], refresh_token=result["refresh_token"],
            expires_in=result["expires_in"], user=_user_out(result["user"], result["roles"]),
        )
    }


@router.post("/mfa/enable", response_model=None)
async def mfa_enable(
    user: AccessTokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user.user_id)))
    db_user = result.scalar_one()
    provisioning_uri, secret = await service.enroll_mfa(db, user=db_user)
    return {"data": MfaEnableResponse(provisioning_uri=provisioning_uri, secret=secret)}


@router.post("/mfa/confirm")
async def mfa_confirm(
    payload: MfaConfirmRequest,
    user: AccessTokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user.user_id)))
    db_user = result.scalar_one()
    await service.confirm_mfa_enrollment(db, user=db_user, code=payload.code)
    return {"data": {"mfa_enabled": True}}


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await service.refresh_tokens(db, raw_refresh_token=payload.refresh_token)
    return {"data": result}


@router.post("/logout")
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await service.logout(db, raw_refresh_token=payload.refresh_token)
    return {"data": {"logged_out": True}}


@router.get("/me", response_model=None)
async def me(
    user: AccessTokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_org_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user.user_id)))
    db_user = result.scalar_one()
    roles = await service.get_user_role_names(db, db_user)
    return {"data": MeResponse(user=_user_out(db_user, roles), permissions=user.permissions)}
