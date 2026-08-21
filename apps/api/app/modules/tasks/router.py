import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_permission
from app.dependencies import get_org_db
from app.modules.tasks import service
from app.modules.tasks.schemas import ApproveTaskRequest, RejectTaskRequest, TaskOut

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=None)
async def list_tasks(
    status: str | None = None,
    user=Depends(require_permission("tasks.read")),
    db: AsyncSession = Depends(get_org_db),
):
    tasks = await service.list_tasks(db, organization_id=uuid.UUID(user.organization_id), status_filter=status)
    return {"data": [TaskOut.model_validate(t) for t in tasks]}


@router.get("/{task_id}", response_model=None)
async def get_task(
    task_id: uuid.UUID,
    user=Depends(require_permission("tasks.read")),
    db: AsyncSession = Depends(get_org_db),
):
    task = await service.get_task(db, organization_id=uuid.UUID(user.organization_id), task_id=task_id)
    return {"data": TaskOut.model_validate(task)}


@router.post("/{task_id}/approve", response_model=None)
async def approve_task(
    task_id: uuid.UUID,
    payload: ApproveTaskRequest,
    user=Depends(require_permission("tasks.approve")),
    db: AsyncSession = Depends(get_org_db),
):
    task = await service.approve_task(
        db, organization_id=uuid.UUID(user.organization_id), task_id=task_id,
        approver_id=uuid.UUID(user.user_id), comment=payload.comment,
    )
    return {"data": TaskOut.model_validate(task)}


@router.post("/{task_id}/reject", response_model=None)
async def reject_task(
    task_id: uuid.UUID,
    payload: RejectTaskRequest,
    user=Depends(require_permission("tasks.approve")),
    db: AsyncSession = Depends(get_org_db),
):
    task = await service.reject_task(
        db, organization_id=uuid.UUID(user.organization_id), task_id=task_id,
        approver_id=uuid.UUID(user.user_id), reason=payload.reason,
    )
    return {"data": TaskOut.model_validate(task)}
