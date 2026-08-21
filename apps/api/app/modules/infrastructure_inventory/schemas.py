from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RegisterServerRequest(BaseModel):
    hostname: str
    ip_address: str | None = None
    os_type: str  # windows | linux
    os_version: str | None = None
    environment: str = "production"
    credential_id: UUID | None = None
    winrm_port: int = 5986
    winrm_use_ssl: bool = True


class ServerOut(BaseModel):
    id: UUID
    organization_id: UUID
    hostname: str
    ip_address: str | None
    os_type: str
    os_version: str | None
    environment: str
    credential_id: UUID | None
    winrm_port: int
    winrm_use_ssl: bool
    health_status: str
    cpu_usage_pct: float | None
    memory_usage_pct: float | None
    disk_usage_pct: float | None
    open_alerts_count: int
    tags: dict
    last_seen_at: datetime | None = None

    class Config:
        from_attributes = True
