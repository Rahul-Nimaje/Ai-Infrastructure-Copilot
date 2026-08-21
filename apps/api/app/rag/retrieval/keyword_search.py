"""PostgreSQL full-text keyword search — complement to vector search
for hybrid retrieval. Uses to_tsvector/to_tsquery against chunk content.

Phase 1: basic keyword search stub.
Phase 3: full hybrid retrieval with score combination.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from py_shared.rag.vector_store import ChunkResult


async def keyword_search(
    db: AsyncSession,
    *,
    query: str,
    organization_id: uuid.UUID,
    top_k: int = 20,
    metadata_filters: dict[str, Any] | None = None,
) -> list[ChunkResult]:
    """Full-text search using PostgreSQL's built-in text search.

    Uses plainto_tsquery for natural language queries (no special syntax needed).
    Results are ranked by ts_rank_cd relevance score.
    """
    query_parts = [
        "SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,",
        "  dc.page_number, dc.section, dc.title, dc.source_type,",
        "  dc.metadata_extra,",
        "  d.title AS document_title, d.file_name,",
        "  ts_rank_cd(to_tsvector('english', dc.content), plainto_tsquery('english', :query)) AS similarity_score",
        "FROM document_chunks dc",
        "JOIN documents d ON d.id = dc.document_id AND d.deleted_at IS NULL",
        "WHERE dc.organization_id = :org_id",
        "  AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', :query)",
    ]
    params: dict[str, Any] = {
        "query": query,
        "org_id": str(organization_id),
    }

    # Optional metadata filters (same as vector store)
    if metadata_filters:
        if "department" in metadata_filters:
            query_parts.append("  AND d.department = :department")
            params["department"] = metadata_filters["department"]
        if "file_type" in metadata_filters:
            query_parts.append("  AND d.file_type = :file_type")
            params["file_type"] = metadata_filters["file_type"]

    query_parts.extend([
        "ORDER BY similarity_score DESC",
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
