import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.department_designation import Department, Designation


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(320))
    username: Mapped[str | None] = mapped_column(String(100), default=None)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="invited")
    employee_id: Mapped[str | None] = mapped_column(String(50), default=None)
    phone_number: Mapped[str | None] = mapped_column(String(30), default=None)
    department: Mapped[str | None] = mapped_column(String(100), default=None)
    designation: Mapped[str | None] = mapped_column(String(100), default=None)
    department_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), default=None)
    designation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("designations.id", ondelete="SET NULL"), default=None)
    profile_picture: Mapped[str | None] = mapped_column(String(500), default=None)

    department_ref: Mapped[Optional["Department"]] = relationship("Department", foreign_keys=[department_id])
    designation_ref: Mapped[Optional["Designation"]] = relationship("Designation", foreign_keys=[designation_id])
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class RefreshToken(Base):
    """Auth-infrastructure table, intentionally not in the core domain schema
    (docs/05-api-design.md Section 2 calls this out explicitly)."""

    __tablename__ = "user_refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(String(255))
    family_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
