from uuid import UUID

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    organization_name: str
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    username: str | None = None
    full_name: str
    status: str
    roles: list[str]
    employee_id: str | None = None
    phone_number: str | None = None
    department: str | None = None
    designation: str | None = None
    profile_picture: str | None = None
    mfa_enabled: bool = False


class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None
    mfa_required: bool = False
    mfa_challenge_id: str | None = None
    user: UserOut | None = None


class MfaEnableResponse(BaseModel):
    provisioning_uri: str
    secret: str  # returned once at enrollment time only, per pyotp convention


class MfaVerifyRequest(BaseModel):
    mfa_challenge_id: str
    code: str


class MfaConfirmRequest(BaseModel):
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    user: UserOut
    permissions: list[str]
