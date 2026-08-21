"""Context builder — assembles the final prompt context from re-ranked chunks
and formats source citations for the LLM and the UI."""
from __future__ import annotations

from app.rag.retrieval.vector_store import ChunkResult


def build_context(chunks: list[ChunkResult], *, max_context_tokens: int = 4000) -> str:
    """Assemble re-ranked chunks into a formatted context string for the LLM.

    Each chunk is prefixed with its source metadata so the LLM can cite them.
    Respects a rough token budget (characters / 4).
    """
    if not chunks:
        return ""

    context_parts: list[str] = []
    token_budget = max_context_tokens
    char_budget = token_budget * 4  # rough approximation

    for i, chunk in enumerate(chunks):
        # Build a source header for citation
        source_header = f"[Source {i + 1}]"
        if chunk.document_title:
            source_header += f" {chunk.document_title}"
        if chunk.file_name:
            source_header += f" ({chunk.file_name})"
        if chunk.page_number:
            source_header += f" — Page {chunk.page_number}"
        if chunk.section:
            source_header += f" — Section: {chunk.section}"

        block = f"{source_header}\n{chunk.content}"

        if len("\n\n".join(context_parts + [block])) > char_budget:
            break

        context_parts.append(block)

    return "\n\n---\n\n".join(context_parts)


def build_source_citations(chunks: list[ChunkResult]) -> list[dict]:
    """Extract source citation metadata from chunks for the UI."""
    seen_docs: set[str] = set()
    citations: list[dict] = []

    for chunk in chunks:
        citation = {
            "document_id": chunk.document_id,
            "document_title": chunk.document_title or "Untitled",
            "file_name": chunk.file_name or "",
            "chunk_id": chunk.chunk_id,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "section": chunk.section,
            "relevance_score": round(chunk.similarity_score, 4),
            "snippet": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
        }
        citations.append(citation)

        # Track unique documents for dedup display
        seen_docs.add(chunk.document_id)

    return citations
