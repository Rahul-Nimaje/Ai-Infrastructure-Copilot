"""Knowledge Base service — business logic for document management and RAG search.

Orchestrates: file storage → parsing → cleaning → chunking → embedding → vector
storage → search → re-ranking → context building → source citations.

Background processing is handled via Celery tasks (app/workers/tasks/document_tasks.py).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.knowledge import repository as repo
from app.rag.chunking.chunker import chunk_document, chunk_pages
from app.rag.embeddings.provider import get_embedding_provider
from app.rag.generation.context_builder import build_context, build_source_citations
from app.rag.ingestion.cleaner import clean_text
from app.rag.ingestion.parser import compute_file_hash, get_file_type, parse_file, validate_file
from app.rag.reranking.reranker import get_reranker
from app.rag.retrieval.vector_store import PgVectorStore

logger = logging.getLogger(__name__)

_vector_store = PgVectorStore()


# ── File Storage ────────────────────────────────────────────────────────

def _ensure_storage_dir() -> Path:
    """Ensure the local storage directory exists."""
    path = Path(settings.file_storage_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _store_file_locally(
    file_bytes: bytes, organization_id: uuid.UUID, file_name: str,
) -> str:
    """Store file to local filesystem. Returns the storage path."""
    storage_dir = _ensure_storage_dir()
    org_dir = storage_dir / str(organization_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    # Use UUID prefix to avoid collisions
    safe_name = f"{uuid.uuid4().hex[:8]}_{file_name}"
    file_path = org_dir / safe_name
    file_path.write_bytes(file_bytes)
    return str(file_path)


def _delete_stored_file(storage_path: str | None) -> None:
    """Remove a file from storage."""
    if storage_path and os.path.exists(storage_path):
        os.remove(storage_path)


def _read_stored_file(storage_path: str) -> bytes:
    """Read file from storage."""
    return Path(storage_path).read_bytes()


# ── Upload ──────────────────────────────────────────────────────────────

async def upload_document(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    file_bytes: bytes,
    file_name: str,
    title: str | None = None,
    department: str | None = None,
    tags: list[str] | None = None,
    metadata_extra: dict | None = None,
) -> dict:
    """Validate, store, and create a document record. Returns immediately
    — actual processing happens in a background Celery task."""

    # Validate
    file_type = get_file_type(file_name)
    if file_type is None:
        raise ValueError(f"Unsupported file type: {file_name}")

    valid, msg = validate_file(file_bytes, file_name, max_size_mb=settings.max_upload_size_mb)
    if not valid:
        raise ValueError(msg)

    # Store file
    storage_path = _store_file_locally(file_bytes, organization_id, file_name)
    file_hash = compute_file_hash(file_bytes)

    # Create DB record
    doc = await repo.create_document(
        db,
        organization_id=organization_id,
        title=title or file_name,
        file_name=file_name,
        file_type=file_type,
        file_size=len(file_bytes),
        file_hash=file_hash,
        storage_path=storage_path,
        uploaded_by=user_id,
        department=department,
        tags=tags,
        metadata_extra=metadata_extra,
    )
    await db.commit()

    # Enqueue background processing
    try:
        from app.workers.tasks.document_tasks import process_document_task
        process_document_task.delay(str(doc.id), str(organization_id))
    except Exception:
        # If Celery is not available, process synchronously (dev mode)
        logger.warning("Celery not available — processing document synchronously")
        await process_document(db, document_id=doc.id, organization_id=organization_id)

    return {
        "id": doc.id,
        "title": doc.title,
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "created_at": doc.created_at,
    }


# ── Background Processing ──────────────────────────────────────────────

async def process_document(
    db: AsyncSession, *, document_id: uuid.UUID, organization_id: uuid.UUID,
) -> None:
    """Full ingestion pipeline: parse → clean → chunk → embed → store vectors.
    Called by the Celery worker or synchronously in dev mode."""

    start_time = time.time()

    # Mark as processing
    await repo.update_document_status(
        db, document_id=document_id, status="processing",
        processing_started_at=datetime.utcnow(),
    )
    await db.commit()

    try:
        # Get document record
        doc = await repo.get_document(db, organization_id=organization_id, document_id=document_id)
        if doc is None:
            raise ValueError(f"Document {document_id} not found")

        # Read file from storage
        if not doc.storage_path:
            raise ValueError("Document has no storage path")
        file_bytes = _read_stored_file(doc.storage_path)

        # Parse
        parsed = await parse_file(file_bytes, doc.file_name, doc.file_type)

        # Clean
        cleaned_text = clean_text(parsed.text)
        if not cleaned_text.strip():
            raise ValueError("Document produced no text after parsing and cleaning")

        # Chunk — use page-aware chunking if we have pages
        if parsed.pages and len(parsed.pages) > 1:
            chunks = chunk_pages(
                [{"page_number": p.page_number, "text": clean_text(p.text)} for p in parsed.pages],
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                source_type=doc.file_type,
            )
        else:
            chunks = chunk_document(
                cleaned_text,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                source_type=doc.file_type,
            )

        if not chunks:
            raise ValueError("Document produced no chunks")

        # Generate embeddings
        embedding_provider = get_embedding_provider()
        chunk_texts = [c.content for c in chunks]
        embeddings = await embedding_provider.embed_texts(chunk_texts)

        # Store chunks with embeddings
        chunk_dicts = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_dicts.append({
                "id": chunk.chunk_id,
                "document_id": str(document_id),
                "chunk_index": i,
                "content": chunk.content,
                "token_count": chunk.token_count,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "title": chunk.title,
                "source_type": chunk.source_type,
                "embedding": embedding,
            })

        await _vector_store.store_chunks(
            db, chunks=chunk_dicts, organization_id=organization_id,
        )

        # Update document status
        elapsed_ms = int((time.time() - start_time) * 1000)
        await repo.update_document_status(
            db, document_id=document_id, status="indexed",
            chunk_count=len(chunks),
            processing_completed_at=datetime.utcnow(),
        )
        await db.commit()

        logger.info(
            "Document %s processed: %d chunks, %d ms",
            document_id, len(chunks), elapsed_ms,
        )

    except Exception as e:
        logger.exception("Failed to process document %s", document_id)
        await repo.update_document_status(
            db, document_id=document_id, status="failed",
            error_message=str(e),
            processing_completed_at=datetime.utcnow(),
        )
        await db.commit()
        raise


# ── Delete ──────────────────────────────────────────────────────────────

async def delete_document(
    db: AsyncSession, *, organization_id: uuid.UUID, document_id: uuid.UUID,
) -> None:
    """Soft-delete document and clean up chunks + stored file."""
    doc = await repo.get_document(db, organization_id=organization_id, document_id=document_id)
    if doc is None:
        raise ValueError("Document not found")

    # Delete chunks from DB
    await repo.delete_chunks_by_document(db, document_id=document_id)

    # Soft-delete the document record
    await repo.soft_delete_document(db, document_id=document_id)

    # Delete stored file
    _delete_stored_file(doc.storage_path)

    await db.commit()


# ── Re-index ────────────────────────────────────────────────────────────

async def reindex_document(
    db: AsyncSession, *, organization_id: uuid.UUID, document_id: uuid.UUID,
) -> None:
    """Drop existing chunks and re-process the document."""
    doc = await repo.get_document(db, organization_id=organization_id, document_id=document_id)
    if doc is None:
        raise ValueError("Document not found")

    # Delete existing chunks
    await repo.delete_chunks_by_document(db, document_id=document_id)
    await repo.update_document_status(db, document_id=document_id, status="pending", chunk_count=0)
    await db.commit()

    # Enqueue re-processing
    try:
        from app.workers.tasks.document_tasks import process_document_task
        process_document_task.delay(str(document_id), str(organization_id))
    except Exception:
        logger.warning("Celery not available — re-indexing synchronously")
        await process_document(db, document_id=document_id, organization_id=organization_id)


# ── RAG Search ──────────────────────────────────────────────────────────

async def search(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    query: str,
    top_k: int | None = None,
    final_top_k: int | None = None,
    metadata_filters: dict | None = None,
    user_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> dict:
    """Full RAG search pipeline: embed → vector search → re-rank → build context."""
    start_time = time.time()

    _top_k = top_k or settings.rag_initial_top_k
    _final_top_k = final_top_k or settings.rag_final_top_k

    # 1. Embed the query
    embedding_provider = get_embedding_provider()
    query_embedding = await embedding_provider.embed_query(query)

    # 2. Vector search
    retrieval_start = time.time()
    results = await _vector_store.search(
        db, embedding=query_embedding, organization_id=organization_id,
        top_k=_top_k, metadata_filters=metadata_filters,
    )
    retrieval_ms = int((time.time() - retrieval_start) * 1000)

    # 3. Re-rank
    reranker = get_reranker()
    reranked = await reranker.rerank(query, results, final_top_k=_final_top_k)

    # 4. Build context and citations
    context = build_context(reranked)
    sources = build_source_citations(reranked)

    total_ms = int((time.time() - start_time) * 1000)

    # 5. Log the query for debugging
    log = await repo.create_query_log(
        db,
        organization_id=organization_id,
        user_id=user_id,
        conversation_id=conversation_id,
        original_query=query,
        metadata_filters=metadata_filters,
        retrieved_chunks=[
            {"chunk_id": r.chunk_id, "score": r.similarity_score, "doc_id": r.document_id}
            for r in reranked
        ],
        final_context=context,
        sources=sources,
        retrieval_time_ms=retrieval_ms,
        total_time_ms=total_ms,
    )
    await db.commit()

    return {
        "query": query,
        "context": context,
        "chunks": [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "content": r.content,
                "similarity_score": r.similarity_score,
                "page_number": r.page_number,
                "section": r.section,
                "document_title": r.document_title,
                "file_name": r.file_name,
            }
            for r in reranked
        ],
        "sources": sources,
        "query_log_id": log.id,
    }
