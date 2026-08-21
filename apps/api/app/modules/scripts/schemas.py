from uuid import UUID

from pydantic import BaseModel


class GenerateScriptRequest(BaseModel):
    description: str
    language: str = "powershell"  # powershell | bash
    target_server_id: UUID | None = None
    conversation_id: UUID | None = None


class CreateScriptRequest(BaseModel):
    name: str
    language: str
    category: str | None = None
    content: str
    risk_level: str = "medium"


class ScriptOut(BaseModel):
    id: UUID
    name: str
    language: str
    category: str | None
    content: str
    version: int
    risk_level: str
    is_ai_generated: bool
    is_approved_template: bool

    class Config:
        from_attributes = True


class ExecuteScriptRequest(BaseModel):
    target_server_id: UUID
    parameters: dict = {}
