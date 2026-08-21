import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.modules.departments import service
from app.modules.departments.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])


@router.get("", response_model=dict[str, Any])
async def list_departments(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    items, total = await service.list_departments(
        db,
        uuid.UUID(current_user.organization_id),
        page=page,
        size=size,
        search=search,
        status_filter=status,
    )
    return {
        "items": [DepartmentResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/active", response_model=list[DepartmentResponse])
async def list_active_departments(
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    items = await service.list_active_departments(db, uuid.UUID(current_user.organization_id))
    return [DepartmentResponse.model_validate(item) for item in items]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    current_user: AccessTokenClaims = Depends(require_permission("users.update")),
    db: AsyncSession = Depends(get_org_db),
):
    item = await service.create_department(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id),
    )
    return DepartmentResponse.model_validate(item)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    current_user: AccessTokenClaims = Depends(require_permission("users.update")),
    db: AsyncSession = Depends(get_org_db),
):
    item = await service.update_department(
        db,
        uuid.UUID(current_user.organization_id),
        department_id,
        payload,
        uuid.UUID(current_user.user_id),
    )
    return DepartmentResponse.model_validate(item)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    department_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("users.delete")),
    db: AsyncSession = Depends(get_org_db),
):
    await service.delete_department(
        db,
        uuid.UUID(current_user.organization_id),
        department_id,
        uuid.UUID(current_user.user_id),
    )
