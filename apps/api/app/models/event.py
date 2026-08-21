import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Event(Base):
    """Normalized cross-source event stream — docs/04-database-design.md
    Section 5.15. Partitioning by occurred_at is a Phase 3 scale concern
    (see docs/04-database-design.md Section 10); Phase 1 uses a plain table."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    server_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("servers.id"), default=None)
    event_source: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))
    raw_payload: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class EventLogEntry(Base):
    """Raw Windows Event Log detail — docs/04-database-design.md Section 6.3."""

    __tablename__ = "event_log_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id"))
    log_channel: Mapped[str] = mapped_column(String(50))
    event_id: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    source_provider: Mapped[str | None] = mapped_column(String(150), default=None)
    message: Mapped[str | None] = mapped_column(Text, default=None)
    raw_xml: Mapped[str | None] = mapped_column(Text, default=None)
    ai_classified_category: Mapped[str | None] = mapped_column(String(100), default=None)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(default=None)
    occurred_at: Mapped[datetime] = mapped_column()
    ingested_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
