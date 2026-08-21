"""RAG Agent — retrieves organization-specific knowledge from the Knowledge Base
and generates grounded answers with source citations.

Runs the retrieval pipeline directly against Postgres (same database and
document_chunks table apps/api's Knowledge Base module writes to) rather than
calling apps/api's /knowledge/search endpoint over HTTP: that endpoint always
derives organization_id from the caller's user JWT (see apps/api/app/dependencies.py
get_org_db — "org_id always comes from the JWT, never a client-supplied
parameter"), so a server-to-server call with no user session could never
authenticate. organization_id reaching this agent has already been validated
upstream by apps/api's ai_chat module before it ever calls this service.
"""
from __future__ import annotations

import logging
import uuid

from app.core.config import settings
from app.core.db import SessionLocal
from py_shared.rag.context_builder import build_context, build_source_citations
from py_shared.rag.embeddings import get_embedding_provider
from py_shared.rag.reranker import get_reranker
from py_shared.rag.vector_store import PgVectorStore

logger = logging.getLogger(__name__)

_vector_store = PgVectorStore()


async def search_knowledge_base(
    *,
    organization_id: uuid.UUID,
    query: str,
    top_k: int = 20,
    final_top_k: int = 6,
    metadata_filters: dict | None = None,
) -> dict:
    """Embed the query, run vector search + re-ranking, and build grounded context."""
    try:
        embedding_provider = get_embedding_provider(
            settings.embedding_provider,
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimension=settings.embedding_dimension,
        )
        query_embedding = await embedding_provider.embed_query(query)

        async with SessionLocal() as db:
            results = await _vector_store.search(
                db, embedding=query_embedding, organization_id=organization_id,
                top_k=top_k, metadata_filters=metadata_filters,
            )

        reranked = await get_reranker().rerank(query, results, final_top_k=final_top_k)

        return {
            "context": build_context(reranked),
            "chunks": [r.content for r in reranked],
            "sources": build_source_citations(reranked),
        }
    except Exception as exc:
        logger.exception("Failed to retrieve RAG knowledge: %s", exc)
        return {"context": "", "chunks": [], "sources": []}
