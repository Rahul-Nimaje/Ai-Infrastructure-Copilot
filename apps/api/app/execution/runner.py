"""The deterministic Execution Service — docs/06-ai-architecture.md Section
2.2, `execution` node: "Invokes the Execution Service (WinRM/SSH), not an LLM
call." Only ever called from app/modules/tasks/service.py after a task's
status has transitioned to "approved". No agent, tool, or endpoint other than
POST /tasks/{id}/approve can reach this function.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.config import settings
from app.core.winrm_client import WinRmTarget, run_powershell
from app.models.infrastructure import Server
from app.models.script import Script
from app.models.task import Task
from app.modules.credentials.service import resolve_credential_secret


async def run_task(db: AsyncSession, *, task: Task, actor_user_id: uuid.UUID) -> Task:
    if task.status != "approved":
        raise ValueError(f"run_task called on task {task.id} with status={task.status}, expected 'approved'")

    if not settings.execution_enabled:
        # Roadmap Phase 1 exit criteria explicitly allow this: script
        # generation + the approval gate work fully; real execution is
        # feature-flagged off until execution-worker hardening is signed off.
        task.status = "execution_skipped_flagged_off"
        task.completed_at = datetime.utcnow()
        await write_audit_log(
            db, organization_id=task.organization_id, actor_type="system", actor_user_id=actor_user_id,
            action="task.execute_skipped_flagged_off", resource_type="task", resource_id=task.id,
            before_state={"status": "approved"}, after_state={"status": task.status},
        )
        await db.commit()
        return task

    task.status = "running"
    task.started_at = datetime.utcnow()
    await db.flush()

    server = (await db.execute(select(Server).where(Server.id == task.target_server_id))).scalar_one()
    script = (await db.execute(select(Script).where(Script.id == task.script_id))).scalar_one()

    try:
        secret = await resolve_credential_secret(
            db, organization_id=task.organization_id, credential_id=server.credential_id
        )
        target = WinRmTarget(
            host=server.hostname, username=secret["username"], password=secret["secret"],
            port=server.winrm_port, ssl=server.winrm_use_ssl,
        )
        stdout, stderr, rc = await run_in_threadpool(run_powershell, target, script.content)
        task.status = "completed" if rc == 0 else "failed"
        task.result = {"stdout": stdout, "stderr": stderr, "return_code": rc}
    except Exception as exc:  # noqa: BLE001 — any connector failure marks the task failed, never silently retried
        task.status = "failed"
        task.result = {"error": str(exc)}

    task.completed_at = datetime.utcnow()
    await write_audit_log(
        db, organization_id=task.organization_id, actor_type="system", actor_user_id=actor_user_id,
        action="task.execute", resource_type="task", resource_id=task.id,
        before_state={"status": "running"}, after_state={"status": task.status, "result": task.result},
    )
    await db.commit()
    return task
