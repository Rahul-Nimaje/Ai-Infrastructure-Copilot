"""Embedding provider abstraction — decouples the application from any
specific embedding API. Shared between apps/api (ingestion) and
apps/ai-orchestrator (query-time retrieval), so both embed with the same
provider/model/dimension.

Providers must satisfy the EmbeddingProvider protocol:
  embed_texts()  — batch embed documents/chunks
  embed_query()  — embed a single search query
  dimension      — vector dimensionality
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol every embedding implementation must satisfy."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts (for document ingestion)."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query (for search)."""
        ...

    @property
    def dimension(self) -> int:
        """The dimensionality of the embedding vectors."""
        ...


class OpenAiEmbeddingProvider:
    """OpenAI text-embedding-3-small (1536 dims) or text-embedding-3-large (3072 dims)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimension = 1536 if "small" in model else 3072

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch, respecting OpenAI's batch limit by chunking."""
        all_embeddings: list[list[float]] = []
        batch_size = 100  # OpenAI limit is ~2048, but 100 is safe and efficient

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Replace empty strings with a placeholder to avoid API errors
            safe_batch = [t if t.strip() else "empty" for t in batch]
            response = await self._client.embeddings.create(
                model=self._model,
                input=safe_batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=[query],
        )
        return response.data[0].embedding

    @property
    def dimension(self) -> int:
        return self._dimension


class LocalEmbeddingProvider:
    """Placeholder for a local embedding model (e.g. sentence-transformers).
    Implemented as a stub that raises NotImplementedError — Phase 2+."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._dimension = 384  # MiniLM default

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Local embedding provider is not yet implemented. "
            "Set EMBEDDING_PROVIDER=openai or implement a sentence-transformers wrapper."
        )

    async def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError("Local embedding provider is not yet implemented.")

    @property
    def dimension(self) -> int:
        return self._dimension


class DummyEmbeddingProvider:
    """Fallback deterministic embedding provider for offline/dev testing without OpenAI API key."""

    def __init__(self, dimension: int = 1536) -> None:
        self._dimension = dimension

    def _hash_vector(self, text: str) -> list[float]:
        import hashlib
        import math
        vec = []
        # Generate deterministic float vector from text hash
        text_bytes = text.encode("utf-8")
        for i in range(self._dimension):
            h = hashlib.sha256(text_bytes + i.to_bytes(4, "little")).digest()
            val = (int.from_bytes(h[:4], "little") / 4294967295.0) * 2.0 - 1.0
            vec.append(val)
        # Normalize vector
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._hash_vector(query)

    @property
    def dimension(self) -> int:
        return self._dimension


def get_embedding_provider(
    provider: str, *, api_key: str = "", model: str = "text-embedding-3-small", dimension: int = 1536,
) -> EmbeddingProvider:
    """Factory — returns the configured embedding provider.

    Takes config values explicitly (rather than importing a settings object)
    since this module is shared by services with separate config schemas.
    """
    if provider in ("dummy", "mock"):
        return DummyEmbeddingProvider(dimension=dimension)

    if provider == "openai":
        if not api_key:
            logger.warning("OPENAI_API_KEY is not set — falling back to DummyEmbeddingProvider for dev mode.")
            return DummyEmbeddingProvider(dimension=dimension)
        return OpenAiEmbeddingProvider(api_key=api_key, model=model)

    if provider == "local":
        return LocalEmbeddingProvider()

    raise ValueError(f"Unknown embedding provider: {provider}")
