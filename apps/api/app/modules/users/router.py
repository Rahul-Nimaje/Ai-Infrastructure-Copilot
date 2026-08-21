import uuid
from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenClaims, get_current_user, require_permission
from app.dependencies import get_org_db
from app.modules.users import service
from app.modules.users.schemas import UserCreate, UserUpdate, UserResponse, UserListResponse, BulkActionRequest

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    department: str | None = None,
    role: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    items, total = await service.list_users(
        db,
        uuid.UUID(current_user.organization_id),
        page=page,
        size=size,
        search=search,
        status_filter=status,
        department=department,
        role_name=role,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return UserListResponse(items=items, total=total, page=page, size=size)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_org_db),
):
    user_detail = await service.get_user_detail(db, uuid.UUID(current_user.organization_id), user_id)
    return UserResponse(**user_detail)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: AccessTokenClaims = Depends(require_permission("users.create")),
    db: AsyncSession = Depends(get_org_db),
):
    user_detail = await service.create_user(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    return UserResponse(**user_detail)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: AccessTokenClaims = Depends(require_permission("users.update")),
    db: AsyncSession = Depends(get_org_db),
):
    user_detail = await service.update_user(
        db,
        uuid.UUID(current_user.organization_id),
        user_id,
        payload,
        uuid.UUID(current_user.user_id)
    )
    return UserResponse(**user_detail)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("users.delete")),
    db: AsyncSession = Depends(get_org_db),
):
    await service.delete_user(
        db,
        uuid.UUID(current_user.organization_id),
        user_id,
        uuid.UUID(current_user.user_id)
    )


@router.post("/bulk")
async def bulk_action(
    payload: BulkActionRequest,
    current_user: AccessTokenClaims = Depends(get_current_user), # enforce check inside service or route
    db: AsyncSession = Depends(get_org_db),
):
    # Enforce action-based permissions
    if payload.action == "delete":
        await require_permission("users.delete")(current_user)
    else:
        await require_permission("users.update")(current_user)

    result = await service.bulk_action(
        db,
        uuid.UUID(current_user.organization_id),
        payload.ids,
        payload.action,
        uuid.UUID(current_user.user_id)
    )
    return result


@router.post("/import")
async def import_users(
    file: UploadFile = File(...),
    current_user: AccessTokenClaims = Depends(require_permission("users.import")),
    db: AsyncSession = Depends(get_org_db),
):
    csv_bytes = await file.read()
    result = await service.import_users_csv(
        db,
        uuid.UUID(current_user.organization_id),
        csv_bytes,
        uuid.UUID(current_user.user_id)
    )
    return result


@router.get("/export/csv")
async def export_users(
    current_user: AccessTokenClaims = Depends(require_permission("users.export")),
    db: AsyncSession = Depends(get_org_db),
):
    csv_content = await service.export_users_csv(db, uuid.UUID(current_user.organization_id))
    
    # Return as streaming csv attachment
    response = StreamingResponse(iter([csv_content]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=users_export.csv"
    return response
