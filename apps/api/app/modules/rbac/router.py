import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.modules.rbac import service
from app.modules.rbac.schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    UserRoleAssignment,
    RolePermissionsUpdate,
    RoleUserResponse,
)

router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    roles = await service.list_roles(db, uuid.UUID(current_user.organization_id))
    return [RoleResponse(**r) for r in roles]


@router.get("/roles/active", response_model=list[RoleResponse])
async def list_active_roles(
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    roles = await service.list_roles(db, uuid.UUID(current_user.organization_id))
    return [RoleResponse(**r) for r in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    role_detail = await service.get_role_detail(db, uuid.UUID(current_user.organization_id), role_id)
    return RoleResponse(**role_detail)


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    current_user: AccessTokenClaims = Depends(require_permission("roles.create")),
    db: AsyncSession = Depends(get_org_db),
):
    role_detail = await service.create_role(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    return RoleResponse(**role_detail)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    current_user: AccessTokenClaims = Depends(require_permission("roles.update")),
    db: AsyncSession = Depends(get_org_db),
):
    role_detail = await service.update_role(
        db,
        uuid.UUID(current_user.organization_id),
        role_id,
        payload,
        uuid.UUID(current_user.user_id)
    )
    return RoleResponse(**role_detail)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("roles.delete")),
    db: AsyncSession = Depends(get_org_db),
):
    await service.delete_role(
        db,
        uuid.UUID(current_user.organization_id),
        role_id,
        uuid.UUID(current_user.user_id)
    )


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    perms = await service.list_permissions(db)
    return [PermissionResponse.model_validate(p) for p in perms]


@router.get("/roles/{role_id}/permissions", response_model=list[PermissionResponse])
async def list_role_permissions(
    role_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    perms = await service.list_role_permissions(
        db, uuid.UUID(current_user.organization_id), role_id
    )
    return perms


@router.put("/roles/{role_id}/permissions", response_model=list[PermissionResponse])
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsUpdate,
    current_user: AccessTokenClaims = Depends(require_permission("roles.update")),
    db: AsyncSession = Depends(get_org_db),
):
    perms = await service.update_role_permissions(
        db,
        uuid.UUID(current_user.organization_id),
        role_id,
        payload.permission_ids,
        uuid.UUID(current_user.user_id)
    )
    return perms


@router.get("/roles/{role_id}/users", response_model=list[RoleUserResponse])
async def list_role_users(
    role_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("roles.read")),
    db: AsyncSession = Depends(get_org_db),
):
    users = await service.list_role_users(
        db, uuid.UUID(current_user.organization_id), role_id
    )
    return users


@router.post("/users/{user_id}/roles")
async def assign_user_roles(
    user_id: uuid.UUID,
    payload: UserRoleAssignment,
    current_user: AccessTokenClaims = Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_org_db),
):
    role_names = await service.assign_user_roles(
        db,
        uuid.UUID(current_user.organization_id),
        user_id,
        payload.role_ids,
        uuid.UUID(current_user.user_id)
    )
    return {"success": True, "roles": role_names}


@router.delete("/users/{user_id}/roles/{role_id}")
async def unassign_user_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("roles.assign")),
    db: AsyncSession = Depends(get_org_db),
):
    await service.unassign_user_role(
        db,
        uuid.UUID(current_user.organization_id),
        user_id,
        role_id,
        uuid.UUID(current_user.user_id)
    )
    return {"success": True}
