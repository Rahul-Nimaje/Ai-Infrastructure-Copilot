from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateConversationRequest(BaseModel):
    title: str | None = None
    module_context: str | None = None


class ConversationOut(BaseModel):
    id: UUID
    title: str | None
    status: str
    last_message_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    referenced_task_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    content: str
