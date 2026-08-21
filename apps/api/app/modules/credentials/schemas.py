from uuid import UUID

from pydantic import BaseModel


class CreateCredentialRequest(BaseModel):
    name: str
    credential_type: str  # winrm | ssh_password | ssh_key | api_key | cloud_iam
    username: str
    secret: str  # password or private key material; never echoed back


class CredentialOut(BaseModel):
    id: UUID
    name: str
    credential_type: str
    username: str | None = None

    class Config:
        from_attributes = True
