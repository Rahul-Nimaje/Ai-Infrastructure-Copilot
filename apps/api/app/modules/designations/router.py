import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.modules.designations import service
from app.modules.designations.schemas import DesignationCreate, DesignationResponse, DesignationUpdate

router = APIRouter(prefix="/api/v1/designations", tags=["designations"])


@router.get("", response_model=dict[str, Any])
async def list_designations(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    departmentId: uuid.UUID | None = Query(None, alias="departmentId"),
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    items, total = await service.list_designations(
        db,
        uuid.UUID(current_user.organization_id),
        department_id=departmentId,
        page=page,
        size=size,
        search=search,
        status_filter=status,
    )
    return {
        "items": [DesignationResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/active", response_model=list[DesignationResponse])
async def list_active_designations(
    departmentId: uuid.UUID | None = Query(None, alias="departmentId"),
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    items = await service.list_active_designations(
        db, uuid.UUID(current_user.organization_id), department_id=departmentId
    )
    return [DesignationResponse.model_validate(item) for item in items]


@router.post("", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED)
async def create_designation(
    payload: DesignationCreate,
    current_user: AccessTokenClaims = Depends(require_permission("users.update")),
    db: AsyncSession = Depends(get_org_db),
):
    item = await service.create_designation(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id),
    )
    return DesignationResponse.model_validate(item)


@router.put("/{designation_id}", response_model=DesignationResponse)
async def update_designation(
    designation_id: uuid.UUID,
    payload: DesignationUpdate,
    current_user: AccessTokenClaims = Depends(require_permission("users.update")),
    db: AsyncSession = Depends(get_org_db),
):
    item = await service.update_designation(
        db,
        uuid.UUID(current_user.organization_id),
        designation_id,
        payload,
        uuid.UUID(current_user.user_id),
    )
    return DesignationResponse.model_validate(item)


@router.delete("/{designation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_designation(
    designation_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("users.delete")),
    db: AsyncSession = Depends(get_org_db),
):
    await service.delete_designation(
        db,
        uuid.UUID(current_user.organization_id),
        designation_id,
        uuid.UUID(current_user.user_id),
    )
