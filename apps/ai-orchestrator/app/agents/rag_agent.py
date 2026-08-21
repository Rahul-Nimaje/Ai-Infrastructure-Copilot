"""RAG Agent — retrieves organization-specific knowledge from the Knowledge Base
and generates grounded answers with source citations.
"""
from __future__ import annotations

import logging
import uuid
import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


async def search_knowledge_base(
    *,
    organization_id: uuid.UUID,
    query: str,
    top_k: int = 20,
    final_top_k: int = 6,
    metadata_filters: dict | None = None,
) -> dict:
    """Query the Knowledge Base search API endpoint on apps/api."""
    api_url = f"{settings.api_base_url}/api/v1/knowledge/search"

    # Call internal API or direct service
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # We pass organization_id header or use internal endpoint call
            response = await client.post(
                api_url,
                json={
                    "query": query,
                    "top_k": top_k,
                    "final_top_k": final_top_k,
                    "metadata_filters": metadata_filters,
                },
                headers={"X-Organization-ID": str(organization_id)},
            )
            if response.status_code == 200:
                body = response.json()
                return body.get("data", {})
        except Exception as e:
            logger.warning("HTTP call to knowledge search failed, falling back to direct DB search: %s", e)

    # Fallback to direct DB retrieval if HTTP call to API fails
    try:
        from app.core.db import SessionLocal
        # Direct service call if running in same context/DB
        from app.modules.knowledge import service as knowledge_service
        async with SessionLocal() as db:
            return await knowledge_service.search(
                db,
                organization_id=organization_id,
                query=query,
                top_k=top_k,
                final_top_k=final_top_k,
                metadata_filters=metadata_filters,
            )
    except Exception as exc:
        logger.exception("Failed to retrieve RAG knowledge: %s", exc)
        return {"context": "", "chunks": [], "sources": []}
