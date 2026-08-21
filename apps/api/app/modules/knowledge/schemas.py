"""Pydantic request/response schemas for the Knowledge Base module."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Upload ──────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime


# ── List / Detail ───────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    department: str | None
    tags: list | None
    chunk_count: int
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailOut(BaseModel):
    id: UUID
    title: str
    file_name: str
    file_type: str
    file_size: int
    file_hash: str | None
    status: str
    error_message: str | None
    department: str | None
    tags: list | None
    metadata_extra: dict | None
    uploaded_by: UUID | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunkOut(BaseModel):
    id: UUID
    chunk_index: int
    content: str
    token_count: int | None
    page_number: int | None
    section: str | None
    title: str | None
    source_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusOut(BaseModel):
    id: UUID
    status: str
    error_message: str | None
    chunk_count: int
    processing_started_at: datetime | None
    processing_completed_at: datetime | None

    class Config:
        from_attributes = True


# ── Search ──────────────────────────────────────────────────────────────

class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=20, ge=1, le=100)
    final_top_k: int = Field(default=6, ge=1, le=50)
    metadata_filters: dict | None = None


class SourceCitationOut(BaseModel):
    document_id: str
    document_title: str
    file_name: str
    chunk_id: str | None
    chunk_index: int | None
    page_number: int | None
    section: str | None
    relevance_score: float | None
    snippet: str | None


class RagSearchResponse(BaseModel):
    query: str
    chunks: list[dict]
    sources: list[SourceCitationOut]
    query_log_id: UUID | None


# ── Filters ─────────────────────────────────────────────────────────────

class DocumentListParams(BaseModel):
    status: str | None = None
    file_type: str | None = None
    department: str | None = None
    search: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── RAG Debug ───────────────────────────────────────────────────────────

class RagQueryLogOut(BaseModel):
    id: UUID
    original_query: str
    transformed_query: str | None
    search_query: str | None
    metadata_filters: dict | None
    retrieved_chunks: list | None
    final_context: str | None
    llm_response: str | None
    sources: list | None
    retrieval_time_ms: int | None
    total_time_ms: int | None
    feedback: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Evaluation ──────────────────────────────────────────────────────────

class RagEvaluationCreate(BaseModel):
    question: str
    expected_doc_id: UUID | None = None
    expected_doc_name: str | None = None


class RagEvaluationOut(BaseModel):
    id: UUID
    question: str
    expected_doc_id: UUID | None
    expected_doc_name: str | None
    actual_doc_ids: list | None
    retrieval_hit: bool | None
    context_relevance: float | None
    answer_relevance: float | None
    citation_accuracy: float | None
    evaluated_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
