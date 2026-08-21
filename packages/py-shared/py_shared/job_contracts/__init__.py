"""Contract for the direct async HTTP call from apps/api to apps/ai-orchestrator.

MVP simplification #2 in the plan: no Redis job queue yet, api calls
ai-orchestrator's POST /run synchronously and proxies its SSE stream.
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RunGraphRequest(BaseModel):
    org_id: UUID
    conversation_id: UUID
    user_id: UUID
    user_prompt: str


# No ResumeGraphRequest: in this implementation the LangGraph run never
# pauses waiting for a decision. It ends after emitting a read-only answer or
# a proposal event; apps/api (app/modules/tasks/service.py +
# app/execution/runner.py) owns the entire human_approval -> execution ->
# audit_log path deterministically once a proposal becomes a persisted Task.
# There is nothing for ai-orchestrator to resume.


class RagSearchRequest(BaseModel):
    """Request from ai-orchestrator to apps/api for RAG retrieval."""

    query: str
    organization_id: UUID
    top_k: int = 20
    final_top_k: int = 6
    metadata_filters: dict | None = None


class RagSearchResponse(BaseModel):
    """Response from apps/api RAG search endpoint."""

    chunks: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    query_log_id: UUID | None = None
