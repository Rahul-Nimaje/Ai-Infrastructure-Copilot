from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ApproveTaskRequest(BaseModel):
    comment: str | None = None


class RejectTaskRequest(BaseModel):
    reason: str


class TaskOut(BaseModel):
    id: UUID
    type: str
    status: str
    target_server_id: UUID | None
    script_id: UUID | None
    execution_method: str | None
    payload: dict
    result: dict | None
    requires_approval: bool
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    rejected_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True
