"""Knowledge Base models — documents, chunks with pgvector embeddings,
RAG query logs, and evaluation test cases. Every row is organization-scoped
for multi-tenant isolation."""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Document(Base):
    """An uploaded knowledge-base document (file-level metadata)."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String(500))
    file_name: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_hash: Mapped[str | None] = mapped_column(String(128), default=None)
    storage_path: Mapped[str | None] = mapped_column(String(1000), default=None)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    department: Mapped[str | None] = mapped_column(String(200), default=None)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    metadata_extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    processing_started_at: Mapped[datetime | None] = mapped_column(default=None)
    processing_completed_at: Mapped[datetime | None] = mapped_column(default=None)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class DocumentChunk(Base):
    """A chunk of text extracted from a document, with its pgvector embedding."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, default=None)
    page_number: Mapped[int | None] = mapped_column(Integer, default=None)
    section: Mapped[str | None] = mapped_column(String(500), default=None)
    title: Mapped[str | None] = mapped_column(String(500), default=None)
    source_type: Mapped[str | None] = mapped_column(String(50), default=None)
    metadata_extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    # pgvector column — 1536 dimensions for text-embedding-3-small
    embedding = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class RagQueryLog(Base):
    """Debug/audit log for every RAG retrieval — used by the RAG debug UI."""

    __tablename__ = "rag_query_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_conversations.id"), default=None
    )
    original_query: Mapped[str] = mapped_column(Text)
    transformed_query: Mapped[str | None] = mapped_column(Text, default=None)
    search_query: Mapped[str | None] = mapped_column(Text, default=None)
    metadata_filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    retrieved_chunks: Mapped[dict] = mapped_column(JSONB, default=list)
    final_context: Mapped[str | None] = mapped_column(Text, default=None)
    llm_response: Mapped[str | None] = mapped_column(Text, default=None)
    sources: Mapped[dict] = mapped_column(JSONB, default=list)
    retrieval_time_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    total_time_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    feedback: Mapped[str | None] = mapped_column(String(20), default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class RagEvaluation(Base):
    """Test question / expected-document pair for evaluating RAG quality."""

    __tablename__ = "rag_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    question: Mapped[str] = mapped_column(Text)
    expected_doc_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id"), default=None
    )
    expected_doc_name: Mapped[str | None] = mapped_column(String(500), default=None)
    actual_doc_ids: Mapped[dict] = mapped_column(JSONB, default=list)
    retrieval_hit: Mapped[bool | None] = mapped_column(Boolean, default=None)
    context_relevance: Mapped[float | None] = mapped_column(Float, default=None)
    answer_relevance: Mapped[float | None] = mapped_column(Float, default=None)
    citation_accuracy: Mapped[float | None] = mapped_column(Float, default=None)
    evaluated_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
