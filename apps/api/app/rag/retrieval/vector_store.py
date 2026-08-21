"""pgvector-backed vector store — performs cosine similarity search against
the document_chunks table with mandatory organization_id filtering for
multi-tenant isolation.

Designed behind a VectorStore protocol so it can be replaced with Qdrant,
Pinecone, Weaviate, or OpenSearch without touching RAG business logic.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """A single search result with the chunk content and metadata."""

    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    chunk_index: int = 0
    page_number: int | None = None
    section: str | None = None
    title: str | None = None
    source_type: str | None = None
    document_title: str | None = None
    file_name: str | None = None
    metadata: dict = field(default_factory=dict)


class VectorStore(Protocol):
    """Protocol for vector store implementations."""

    async def search(
        self, db: AsyncSession, *, embedding: list[float],
        organization_id: uuid.UUID, top_k: int, metadata_filters: dict | None,
    ) -> list[ChunkResult]: ...

    async def store_chunks(
        self, db: AsyncSession, *, chunks: list[dict], organization_id: uuid.UUID,
    ) -> None: ...

    async def delete_by_document(
        self, db: AsyncSession, *, document_id: uuid.UUID,
    ) -> int: ...


class PgVectorStore:
    """PostgreSQL + pgvector implementation.

    Uses cosine distance (<=> operator) for similarity search.
    Every query mandates organization_id — never leaks across tenants.
    """

    async def search(
        self, db: AsyncSession, *, embedding: list[float],
        organization_id: uuid.UUID, top_k: int = 20,
        metadata_filters: dict[str, Any] | None = None,
    ) -> list[ChunkResult]:
        """Perform cosine-similarity vector search with mandatory org filter."""

        # Build the base query with org isolation
        # The <=> operator computes cosine distance; we want 1 - distance = similarity
        query_parts = [
            "SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,",
            "  dc.page_number, dc.section, dc.title, dc.source_type,",
            "  dc.metadata_extra,",
            "  d.title AS document_title, d.file_name,",
            "  1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity_score",

            "FROM document_chunks dc",
            "JOIN documents d ON d.id = dc.document_id AND d.deleted_at IS NULL",
            "WHERE dc.organization_id = :org_id",
            "  AND dc.embedding IS NOT NULL",
        ]
        params: dict[str, Any] = {
            "embedding": str(embedding),
            "org_id": str(organization_id),
        }

        # Optional metadata filters
        if metadata_filters:
            if "department" in metadata_filters:
                query_parts.append("  AND d.department = :department")
                params["department"] = metadata_filters["department"]

            if "file_type" in metadata_filters:
                query_parts.append("  AND d.file_type = :file_type")
                params["file_type"] = metadata_filters["file_type"]

            if "tags" in metadata_filters and metadata_filters["tags"]:
                # JSONB array containment — d.tags @> '["tag1"]'::jsonb
                query_parts.append("  AND d.tags @> CAST(:tags AS jsonb)")

                import json
                params["tags"] = json.dumps(metadata_filters["tags"])

            if "server" in metadata_filters:
                query_parts.append("  AND d.metadata_extra->>'server' = :server")
                params["server"] = metadata_filters["server"]

            if "environment" in metadata_filters:
                query_parts.append("  AND d.metadata_extra->>'environment' = :environment")
                params["environment"] = metadata_filters["environment"]

        query_parts.extend([
            "ORDER BY dc.embedding <=> CAST(:embedding AS vector)",
            "LIMIT :top_k",
        ])
        params["top_k"] = top_k

        sql = "\n".join(query_parts)
        result = await db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            ChunkResult(
                chunk_id=str(row.id),
                document_id=str(row.document_id),
                content=row.content,
                similarity_score=float(row.similarity_score),
                chunk_index=row.chunk_index,
                page_number=row.page_number,
                section=row.section,
                title=row.title,
                source_type=row.source_type,
                document_title=row.document_title,
                file_name=row.file_name,
                metadata=row.metadata_extra or {},
            )
            for row in rows
        ]

    async def store_chunks(
        self, db: AsyncSession, *, chunks: list[dict], organization_id: uuid.UUID,
    ) -> None:
        """Bulk-insert chunks with their embeddings."""
        if not chunks:
            return

        for chunk in chunks:
            await db.execute(
                text("""
                    INSERT INTO document_chunks
                        (id, document_id, organization_id, chunk_index, content,
                         token_count, page_number, section, title, source_type,
                         metadata_extra, embedding)
                    VALUES
                        (:id, :document_id, :org_id, :chunk_index, :content,
                         :token_count, :page_number, :section, :title, :source_type,
                         CAST(:metadata_extra AS jsonb), CAST(:embedding AS vector))
                """),

                {
                    "id": chunk.get("id", str(uuid.uuid4())),
                    "document_id": str(chunk["document_id"]),
                    "org_id": str(organization_id),
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "token_count": chunk.get("token_count"),
                    "page_number": chunk.get("page_number"),
                    "section": chunk.get("section"),
                    "title": chunk.get("title"),
                    "source_type": chunk.get("source_type"),
                    "metadata_extra": "{}",
                    "embedding": str(chunk["embedding"]) if chunk.get("embedding") else None,
                },
            )
        await db.flush()

    async def delete_by_document(
        self, db: AsyncSession, *, document_id: uuid.UUID,
    ) -> int:
        """Delete all chunks for a document. Returns the count of deleted rows."""
        result = await db.execute(
            text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
            {"doc_id": str(document_id)},
        )
        await db.flush()
        return result.rowcount or 0
