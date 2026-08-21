from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DesignationCreate(BaseModel):
    department_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    status: str = Field("active", max_length=20)


class DesignationUpdate(BaseModel):
    department_id: UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    status: str | None = Field(None, max_length=20)


class DesignationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    department_id: UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    department_name: str | None = None

    class Config:
        from_attributes = True
