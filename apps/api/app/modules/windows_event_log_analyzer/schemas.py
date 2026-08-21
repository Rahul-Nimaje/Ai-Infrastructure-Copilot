from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EventLogEntryOut(BaseModel):
    id: int
    server_id: UUID
    log_channel: str
    event_id: int
    level: str
    source_provider: str | None
    message: str | None
    occurred_at: datetime

    class Config:
        from_attributes = True
