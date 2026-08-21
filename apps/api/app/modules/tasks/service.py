import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.execution.runner import run_task
from app.models.task import Task
from app.socket_app import emit_to_org


async def list_tasks(db: AsyncSession, *, organization_id: uuid.UUID, status_filter: str | None = None) -> list[Task]:
    query = select(Task).where(Task.organization_id == organization_id)
    if status_filter:
        query = query.where(Task.status == status_filter)
    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_task(db: AsyncSession, *, organization_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id, Task.organization_id == organization_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Task not found."})
    return task


async def approve_task(db: AsyncSession, *, organization_id: uuid.UUID, task_id: uuid.UUID, approver_id: uuid.UUID, comment: str | None) -> Task:
    task = await get_task(db, organization_id=organization_id, task_id=task_id)
    if task.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Task is '{task.status}', not 'pending_approval'."},
        )
    task.status = "approved"
    task.approved_by_user_id = approver_id
    task.approved_at = datetime.utcnow()
    await write_audit_log(
        db, organization_id=organization_id, actor_type="user", actor_user_id=approver_id,
        action="task.approve", resource_type="task", resource_id=task.id,
        before_state={"status": "pending_approval"}, after_state={"status": "approved", "comment": comment},
    )
    await db.commit()

    task = await run_task(db, task=task, actor_user_id=approver_id)
    await emit_to_org(
        "approval.resolved", {"task_id": str(task.id), "decision": "approved", "status": task.status},
        organization_id=organization_id,
    )
    return task


async def reject_task(db: AsyncSession, *, organization_id: uuid.UUID, task_id: uuid.UUID, approver_id: uuid.UUID, reason: str) -> Task:
    task = await get_task(db, organization_id=organization_id, task_id=task_id)
    if task.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail={"code": "CONFLICT", "message": f"Task is '{task.status}', not 'pending_approval'."},
        )
    task.status = "rejected"
    task.rejected_reason = reason
    task.approved_by_user_id = approver_id
    task.approved_at = datetime.utcnow()
    await write_audit_log(
        db, organization_id=organization_id, actor_type="user", actor_user_id=approver_id,
        action="task.reject", resource_type="task", resource_id=task.id,
        before_state={"status": "pending_approval"}, after_state={"status": "rejected", "reason": reason},
    )
    await db.commit()
    await emit_to_org(
        "approval.resolved", {"task_id": str(task.id), "decision": "rejected", "status": task.status},
        organization_id=organization_id,
    )
    return task
