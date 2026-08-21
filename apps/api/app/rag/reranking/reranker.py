"""Re-ranking — takes the initial top-K retrieved chunks and re-scores them
to select the final top-N most relevant chunks for the LLM context.

Phase 1: SimpleReranker — keyword overlap + position heuristic.
Phase 3: LlmReranker — uses the configured LLM to score relevance.
"""
from __future__ import annotations

import re
from typing import Protocol

from app.rag.retrieval.vector_store import ChunkResult


class Reranker(Protocol):
    """Protocol for re-ranking implementations."""

    async def rerank(
        self, query: str, chunks: list[ChunkResult], *, final_top_k: int,
    ) -> list[ChunkResult]: ...


class SimpleReranker:
    """Lightweight re-ranker using keyword overlap scoring combined with
    the original similarity score. No LLM calls — fast and free.

    Score = 0.7 * similarity_score + 0.3 * keyword_overlap_ratio
    """

    async def rerank(
        self, query: str, chunks: list[ChunkResult], *, final_top_k: int = 6,
    ) -> list[ChunkResult]:
        if not chunks:
            return []

        query_terms = set(self._tokenize(query.lower()))
        if not query_terms:
            # If no meaningful terms, just return top by similarity
            return sorted(chunks, key=lambda c: c.similarity_score, reverse=True)[:final_top_k]

        scored: list[tuple[float, ChunkResult]] = []
        for chunk in chunks:
            chunk_terms = set(self._tokenize(chunk.content.lower()))
            # Keyword overlap ratio
            if chunk_terms:
                overlap = len(query_terms & chunk_terms) / len(query_terms)
            else:
                overlap = 0.0

            # Combined score
            combined = 0.7 * chunk.similarity_score + 0.3 * overlap
            scored.append((combined, chunk))

        # Sort by combined score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Deduplicate: remove chunks with near-identical content from the same doc
        seen_content_hashes: set[str] = set()
        unique_results: list[ChunkResult] = []
        for score, chunk in scored:
            content_hash = chunk.content[:200].strip()
            if content_hash not in seen_content_hashes:
                seen_content_hashes.add(content_hash)
                chunk.similarity_score = score  # Update with combined score
                unique_results.append(chunk)
            if len(unique_results) >= final_top_k:
                break

        return unique_results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenization — split on non-alphanumeric characters,
        filter stopwords and short tokens."""
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "and", "or", "but", "nor", "not", "so", "yet", "for", "at",
            "by", "from", "in", "into", "of", "on", "to", "with", "up",
            "out", "if", "then", "than", "too", "very", "just", "about",
            "what", "which", "who", "whom", "this", "that", "these",
            "those", "it", "its", "my", "our", "your", "his", "her",
            "their", "we", "you", "he", "she", "they", "me", "him",
            "us", "them", "how", "when", "where", "why",
        }
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        return [t for t in tokens if t not in stopwords and len(t) > 2]


def get_reranker() -> Reranker:
    """Factory — returns the configured re-ranker. Phase 1 uses SimpleReranker."""
    return SimpleReranker()
