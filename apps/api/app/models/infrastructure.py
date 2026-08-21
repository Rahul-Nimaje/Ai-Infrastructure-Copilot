import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    hostname: Mapped[str] = mapped_column(String(255))
    # Plain VARCHAR rather than Postgres INET: avoids relying on unverified
    # asyncpg/SQLAlchemy inet<->str codec behavior offline, and Phase 1 never
    # does subnet arithmetic on this column.
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    os_type: Mapped[str] = mapped_column(String(20))
    os_version: Mapped[str | None] = mapped_column(String(100), default=None)
    environment: Mapped[str] = mapped_column(String(30), default="production")
    credential_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("credentials.id"), default=None)
    # Per-server WinRM connection settings — not in docs/04-database-design.md
    # (that doc doesn't get this granular); added because HTTPS:5986 requires
    # a cert on the target that most lab/test boxes don't have configured.
    winrm_port: Mapped[int] = mapped_column(Integer, default=5986)
    winrm_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown")
    cpu_usage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    memory_usage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    disk_usage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    open_alerts_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    tags: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class InfrastructureInventory(Base):
    """Polymorphic cross-module asset catalog — docs/04-database-design.md
    Section 5.21. Phase 1 only ever writes asset_type='server' rows."""

    __tablename__ = "infrastructure_inventory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    asset_type: Mapped[str] = mapped_column(String(30))
    asset_id: Mapped[uuid.UUID] = mapped_column()
    discovered_via: Mapped[str] = mapped_column(String(30), default="manual")
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_scanned_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
