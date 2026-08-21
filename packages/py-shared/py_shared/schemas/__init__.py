"""Pydantic models shared between apps/api and apps/ai-orchestrator.

These mirror the CopilotState fields in docs/06-ai-architecture.md Section 2.1
that actually cross the process boundary between the two services.
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from py_shared.enums import RiskLevel


class ServerSummary(BaseModel):
    id: UUID
    hostname: str
    os_type: str
    os_version: str | None = None
    health_status: str


class EventLogEntrySummary(BaseModel):
    id: int
    log_channel: str
    event_id: int
    level: str
    source_provider: str | None = None
    message: str | None = None
    occurred_at: str


class RootCause(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]


class Recommendation(BaseModel):
    action: str
    rationale: str
    risk_level: RiskLevel
    requires_script: bool


class ProposedScript(BaseModel):
    task_id: UUID
    script_id: UUID
    language: Literal["powershell", "bash"]
    content: str
    risk_level: RiskLevel
    explanation: str
    rollback_plan: str


class AgentStepEvent(BaseModel):
    """One SSE event emitted while the graph runs. Maps 1:1 to the `event:`
    frames documented in docs/05-api-design.md Section 11."""

    event: Literal["agent_step", "token", "task_created", "rag_sources", "done", "error"]
    data: dict[str, Any]


class SourceCitation(BaseModel):
    """A single source reference attached to a RAG-grounded answer."""

    document_id: UUID
    document_title: str
    file_name: str
    chunk_id: UUID | None = None
    chunk_index: int | None = None
    page_number: int | None = None
    section: str | None = None
    relevance_score: float | None = None
    snippet: str | None = None


class RagContext(BaseModel):
    """Retrieved context sent from the RAG Agent back to the coordinator."""

    chunks: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[SourceCitation] = Field(default_factory=list)
    query_log_id: UUID | None = None
