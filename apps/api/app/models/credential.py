import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Credential(Base):
    """See docs/04-database-design.md Section 4 and app/core/vault.py for the
    local_encrypted MVP resolver used behind vault_engine/vault_path."""

    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String(255))
    credential_type: Mapped[str] = mapped_column(String(30))
    vault_engine: Mapped[str] = mapped_column(String(30), default="local_encrypted")
    vault_path: Mapped[str] = mapped_column(String(500))
    vault_key_version: Mapped[int] = mapped_column(Integer, default=1)
    encrypted_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    rotation_policy: Mapped[str | None] = mapped_column(String(30), default="manual")
    last_rotated_at: Mapped[datetime | None] = mapped_column(default=None)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
