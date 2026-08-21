import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_permission
from app.dependencies import get_org_db
from app.modules.scripts import service
from app.modules.scripts.schemas import (
    CreateScriptRequest,
    ExecuteScriptRequest,
    GenerateScriptRequest,
    ScriptOut,
)

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])


@router.get("", response_model=None)
async def list_scripts(
    user=Depends(require_permission("scripts.read")),
    db: AsyncSession = Depends(get_org_db),
):
    scripts = await service.list_scripts(db, organization_id=uuid.UUID(user.organization_id))
    return {"data": [ScriptOut.model_validate(s) for s in scripts]}


@router.get("/{script_id}", response_model=None)
async def get_script(
    script_id: uuid.UUID,
    user=Depends(require_permission("scripts.read")),
    db: AsyncSession = Depends(get_org_db),
):
    script = await service.get_script(db, organization_id=uuid.UUID(user.organization_id), script_id=script_id)
    if script is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Script not found."})
    return {"data": ScriptOut.model_validate(script)}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_script(
    payload: CreateScriptRequest,
    user=Depends(require_permission("scripts.write")),
    db: AsyncSession = Depends(get_org_db),
):
    script = await service.create_script(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id),
        name=payload.name, language=payload.language, category=payload.category,
        content=payload.content, risk_level=payload.risk_level,
    )
    return {"data": ScriptOut.model_validate(script)}


@router.post("/generate", status_code=status.HTTP_201_CREATED, response_model=None)
async def generate_script(
    payload: GenerateScriptRequest,
    user=Depends(require_permission("scripts.write")),
    db: AsyncSession = Depends(get_org_db),
):
    script = await service.generate_script(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id),
        description=payload.description, language=payload.language,
    )
    return {"data": ScriptOut.model_validate(script)}


@router.post("/{script_id}/execute", status_code=status.HTTP_202_ACCEPTED, response_model=None)
async def execute_script(
    script_id: uuid.UUID,
    payload: ExecuteScriptRequest,
    user=Depends(require_permission("scripts.execute")),
    db: AsyncSession = Depends(get_org_db),
):
    task = await service.request_execution(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id),
        script_id=script_id, target_server_id=payload.target_server_id, parameters=payload.parameters,
    )
    return {
        "data": {
            "task_id": str(task.id), "type": task.type, "status": task.status,
            "script_id": str(script_id), "target_server_id": str(payload.target_server_id),
            "execution_method": task.execution_method, "requires_approval": task.requires_approval,
            "created_at": task.created_at.isoformat(),
        }
    }
