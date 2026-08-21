from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    status: str = Field("active", max_length=20)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    status: str | None = Field(None, max_length=20)


class DepartmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
