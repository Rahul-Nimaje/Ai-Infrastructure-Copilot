from uuid import UUID
from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    permissions: list[UUID] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    permissions: list[UUID] | None = None


class RoleResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_system_role: bool
    permissions: list[str] = []  # permission codes

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    module: str
    description: str | None

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    role_ids: list[UUID]


class RolePermissionsUpdate(BaseModel):
    permission_ids: list[UUID]


class RoleUserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    username: str | None = None
    full_name: str
    status: str

    class Config:
        from_attributes = True
