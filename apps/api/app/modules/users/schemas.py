from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, description="Password policy requires 8+ characters")
    employee_id: str | None = None
    phone_number: str | None = None
    department: str | None = None
    designation: str | None = None
    department_id: UUID
    designation_id: UUID
    profile_picture: str | None = None
    status: str = "active"
    roles: list[str] = Field(..., min_length=1, description="At least one role name is required")


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=100)
    full_name: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=8)
    employee_id: str | None = None
    phone_number: str | None = None
    department: str | None = None
    designation: str | None = None
    department_id: UUID | None = None
    designation_id: UUID | None = None
    profile_picture: str | None = None
    status: str | None = None
    roles: list[str] | None = None


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    username: str | None
    full_name: str
    status: str
    employee_id: str | None
    phone_number: str | None
    department: str | None
    designation: str | None
    department_id: UUID | None
    designation_id: UUID | None
    profile_picture: str | None
    mfa_enabled: bool
    roles: list[str]
    created_by_id: UUID | None
    updated_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int


class BulkActionRequest(BaseModel):
    ids: list[UUID]
    action: str  # delete | activate | deactivate
