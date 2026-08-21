import uuid

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.config import settings
from app.models.script import Script
from app.models.task import Task
from app.socket_app import emit_to_org


async def list_scripts(db: AsyncSession, *, organization_id: uuid.UUID) -> list[Script]:
    result = await db.execute(
        select(Script).where(Script.organization_id == organization_id, Script.deleted_at.is_(None))
        .order_by(Script.created_at.desc())
    )
    return list(result.scalars().all())


async def get_script(db: AsyncSession, *, organization_id: uuid.UUID, script_id: uuid.UUID) -> Script | None:
    result = await db.execute(
        select(Script).where(Script.id == script_id, Script.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def create_script(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, name: str, language: str,
    category: str | None, content: str, risk_level: str, is_ai_generated: bool = False,
) -> Script:
    script = Script(
        organization_id=organization_id, name=name, language=language, category=category,
        content=content, risk_level=risk_level, is_ai_generated=is_ai_generated,
        created_by_user_id=user_id,
    )
    db.add(script)
    await db.commit()
    await db.refresh(script)
    return script


async def generate_script(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, description: str, language: str,
) -> Script:
    """Proxies to apps/ai-orchestrator's PowerShell Agent / mcp_scripting tools
    (docs/06-ai-architecture.md Section 3, PowerShell Agent) — this endpoint
    calls the tool directly rather than the full LangGraph diagnosis graph,
    since the PowerShell Generator module (docs/03-LLD.md Module 10) is a
    direct "describe what you want, get a script" flow, not a diagnosis."""
    try:
        async with httpx.AsyncClient(base_url=settings.ai_orchestrator_url, timeout=60.0) as client:
            response = await client.post(
                "/tools/powershell/generate", json={"description": description, "language": language}
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as exc:
        # Most commonly a missing/invalid LLM provider credential on
        # ai-orchestrator (e.g. OPENAI_API_KEY unset) — surface the
        # documented error envelope instead of an opaque 500.
        raise HTTPException(
            status_code=502,
            detail={"code": "INTERNAL_ERROR", "message": f"Script generation failed: {exc.response.text}"},
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "INTERNAL_ERROR", "message": f"Could not reach the AI orchestrator: {exc}"},
        ) from exc

    return await create_script(
        db, organization_id=organization_id, user_id=user_id, name=result.get("name", description[:80]),
        language=language, category=result.get("category"), content=result["content"],
        risk_level=result["risk_level"], is_ai_generated=True,
    )


async def request_execution(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, script_id: uuid.UUID,
    target_server_id: uuid.UUID, parameters: dict,
) -> Task:
    """Implements the Human Approval gate exactly as docs/05-api-design.md
    Section 6 describes: low-risk read-only scripts auto-run (status=
    completed immediately is out of scope for Phase 1 execution — see
    app/execution/runner.py), everything else becomes pending_approval."""
    script = await get_script(db, organization_id=organization_id, script_id=script_id)
    if script is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Script not found."})
    execution_method = "winrm"  # Phase 1 targets Windows only

    task = Task(
        organization_id=organization_id,
        type="script_execution",
        status="pending_approval",
        target_server_id=target_server_id,
        script_id=script_id,
        execution_method=execution_method,
        payload={"parameters": parameters},
        requires_approval=script.risk_level != "low",
        requested_by_user_id=user_id,
    )
    db.add(task)
    await db.flush()
    await write_audit_log(
        db, organization_id=organization_id, actor_type="user", actor_user_id=user_id,
        action="task.request", resource_type="task", resource_id=task.id,
        after_state={"status": task.status, "script_id": str(script_id)},
    )
    await db.commit()
    await db.refresh(task)
    await emit_to_org(
        "approval.requested",
        {
            "task_id": str(task.id), "summary": script.name,
            "risk_level": script.risk_level, "target_server_id": str(target_server_id),
        },
        organization_id=organization_id,
    )
    return task
