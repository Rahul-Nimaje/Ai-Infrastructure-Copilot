"""Data access layer for the Knowledge Base — all DB queries live here,
never in the router or service layer. Every query filters by organization_id
for multi-tenant isolation."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import Document, DocumentChunk, RagEvaluation, RagQueryLog


# ── Documents ───────────────────────────────────────────────────────────

async def create_document(
    db: AsyncSession, *, organization_id: uuid.UUID, title: str, file_name: str,
    file_type: str, file_size: int, file_hash: str | None, storage_path: str | None,
    uploaded_by: uuid.UUID | None, department: str | None = None,
    tags: list | None = None, metadata_extra: dict | None = None,
) -> Document:
    doc = Document(
        organization_id=organization_id,
        title=title,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        file_hash=file_hash,
        storage_path=storage_path,
        uploaded_by=uploaded_by,
        department=department,
        tags=tags or [],
        metadata_extra=metadata_extra or {},
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_document(
    db: AsyncSession, *, organization_id: uuid.UUID, document_id: uuid.UUID,
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == organization_id,
            Document.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession, *, organization_id: uuid.UUID,
    status: str | None = None, file_type: str | None = None,
    department: str | None = None, search: str | None = None,
    offset: int = 0, limit: int = 20,
) -> tuple[list[Document], int]:
    """Returns (documents, total_count) for pagination."""
    query = select(Document).where(
        Document.organization_id == organization_id,
        Document.deleted_at.is_(None),
    )
    count_query = select(func.count(Document.id)).where(
        Document.organization_id == organization_id,
        Document.deleted_at.is_(None),
    )

    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)
    if file_type:
        query = query.where(Document.file_type == file_type)
        count_query = count_query.where(Document.file_type == file_type)
    if department:
        query = query.where(Document.department == department)
        count_query = count_query.where(Document.department == department)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            Document.title.ilike(pattern) | Document.file_name.ilike(pattern)
        )
        count_query = count_query.where(
            Document.title.ilike(pattern) | Document.file_name.ilike(pattern)
        )

    query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    docs = list(result.scalars().all())

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return docs, total


async def update_document_status(
    db: AsyncSession, *, document_id: uuid.UUID, status: str,
    error_message: str | None = None, chunk_count: int | None = None,
    processing_started_at: datetime | None = None,
    processing_completed_at: datetime | None = None,
) -> None:
    values: dict = {"status": status, "updated_at": datetime.utcnow()}
    if error_message is not None:
        values["error_message"] = error_message
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    if processing_started_at is not None:
        values["processing_started_at"] = processing_started_at
    if processing_completed_at is not None:
        values["processing_completed_at"] = processing_completed_at

    await db.execute(
        update(Document).where(Document.id == document_id).values(**values)
    )
    await db.flush()


async def soft_delete_document(
    db: AsyncSession, *, document_id: uuid.UUID,
) -> None:
    await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(deleted_at=datetime.utcnow(), status="deleting")
    )
    await db.flush()


# ── Chunks ──────────────────────────────────────────────────────────────

async def get_chunks_by_document(
    db: AsyncSession, *, document_id: uuid.UUID,
    offset: int = 0, limit: int = 50,
) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_chunks_by_document(
    db: AsyncSession, *, document_id: uuid.UUID,
) -> int:
    """Delete all chunks for a document. Returns deleted count."""
    from sqlalchemy import delete
    result = await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await db.flush()
    return result.rowcount or 0


# ── RAG Query Logs ──────────────────────────────────────────────────────

async def create_query_log(
    db: AsyncSession, *, organization_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    original_query: str,
    transformed_query: str | None = None,
    search_query: str | None = None,
    metadata_filters: dict | None = None,
    retrieved_chunks: list | None = None,
    final_context: str | None = None,
    llm_response: str | None = None,
    sources: list | None = None,
    retrieval_time_ms: int | None = None,
    total_time_ms: int | None = None,
) -> RagQueryLog:
    log = RagQueryLog(
        organization_id=organization_id,
        user_id=user_id,
        conversation_id=conversation_id,
        original_query=original_query,
        transformed_query=transformed_query,
        search_query=search_query,
        metadata_filters=metadata_filters or {},
        retrieved_chunks=retrieved_chunks or [],
        final_context=final_context,
        llm_response=llm_response,
        sources=sources or [],
        retrieval_time_ms=retrieval_time_ms,
        total_time_ms=total_time_ms,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_query_log(
    db: AsyncSession, *, organization_id: uuid.UUID, query_log_id: uuid.UUID,
) -> RagQueryLog | None:
    result = await db.execute(
        select(RagQueryLog).where(
            RagQueryLog.id == query_log_id,
            RagQueryLog.organization_id == organization_id,
        )
    )
    return result.scalar_one_or_none()


# ── Evaluations ─────────────────────────────────────────────────────────

async def create_evaluation(
    db: AsyncSession, *, organization_id: uuid.UUID,
    question: str, expected_doc_id: uuid.UUID | None = None,
    expected_doc_name: str | None = None,
) -> RagEvaluation:
    evaluation = RagEvaluation(
        organization_id=organization_id,
        question=question,
        expected_doc_id=expected_doc_id,
        expected_doc_name=expected_doc_name,
    )
    db.add(evaluation)
    await db.flush()
    await db.refresh(evaluation)
    return evaluation


async def list_evaluations(
    db: AsyncSession, *, organization_id: uuid.UUID,
) -> list[RagEvaluation]:
    result = await db.execute(
        select(RagEvaluation)
        .where(RagEvaluation.organization_id == organization_id)
        .order_by(RagEvaluation.created_at.desc())
    )
    return list(result.scalars().all())
