"""Intelligent document chunking — preserves headings, sections, paragraphs,
code blocks, tables, and lists instead of blindly splitting by character count.

Uses a hierarchical splitting strategy:
1. Split by headings (H1-H6 or equivalent markers)
2. Within sections, split by paragraphs
3. Within paragraphs, split by sentences if still too large
4. Code blocks and tables are kept atomic when possible
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Chunk:
    """A single chunk of text with positional and structural metadata."""

    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    chunk_index: int = 0
    content: str = ""
    token_count: int = 0
    page_number: int | None = None
    section: str | None = None
    title: str | None = None
    source_type: str | None = None
    metadata: dict = field(default_factory=dict)


class ChunkingStrategy(Protocol):
    """Protocol for chunking strategies."""

    def chunk(self, text: str, *, chunk_size: int, chunk_overlap: int,
              page_number: int | None, source_type: str | None) -> list[Chunk]: ...


def estimate_tokens(text: str) -> int:
    """Rough token estimation — ~4 characters per token for English.
    For production, use tiktoken, but this avoids the dependency for
    basic operation."""
    return max(1, len(text) // 4)


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split text by heading markers (Markdown # or underlined headings).
    Returns list of (heading, section_body) tuples."""

    # Match Markdown headings: # Heading, ## Heading, etc.
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []

    # Content before first heading
    pre_heading = text[:matches[0].start()].strip()
    if pre_heading:
        sections.append((None, pre_heading))

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((heading, body))

    return sections


def _is_code_block(text: str) -> bool:
    """Check if text is a fenced code block."""
    stripped = text.strip()
    return stripped.startswith("```") and stripped.endswith("```")


def _is_table(text: str) -> bool:
    """Check if text looks like a Markdown table."""
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return False
    return all("|" in line for line in lines[:3])


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, keeping code blocks and tables intact."""
    # First, protect code blocks from splitting
    code_block_pattern = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    protected_blocks: list[str] = []
    placeholder_text = text

    for match in code_block_pattern.finditer(text):
        placeholder = f"__CODE_BLOCK_{len(protected_blocks)}__"
        protected_blocks.append(match.group())
        placeholder_text = placeholder_text.replace(match.group(), placeholder, 1)

    # Split by double newlines
    raw_paragraphs = re.split(r"\n\n+", placeholder_text)

    # Restore code blocks
    paragraphs: list[str] = []
    for para in raw_paragraphs:
        for i, block in enumerate(protected_blocks):
            para = para.replace(f"__CODE_BLOCK_{i}__", block)
        stripped = para.strip()
        if stripped:
            paragraphs.append(stripped)

    return paragraphs


def _split_sentences(text: str, chunk_size: int) -> list[str]:
    """Split text into sentence-level chunks when paragraphs are too long."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if current_tokens + sentence_tokens > chunk_size and current:
            chunks.append(" ".join(current))
            # Overlap: keep the last sentence
            current = [current[-1]] if current else []
            current_tokens = estimate_tokens(current[0]) if current else 0
        current.append(sentence)
        current_tokens += sentence_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks


class SemanticChunker:
    """Hierarchical chunker that preserves document structure.

    Splitting order:
    1. By heading sections
    2. By paragraphs within sections
    3. By sentences within large paragraphs
    Code blocks and tables are kept as atomic units.
    """

    def chunk(
        self, text: str, *, chunk_size: int = 512, chunk_overlap: int = 50,
        page_number: int | None = None, source_type: str | None = None,
    ) -> list[Chunk]:
        sections = _split_into_sections(text)
        chunks: list[Chunk] = []
        idx = 0

        for heading, body in sections:
            paragraphs = _split_paragraphs(body)
            current_content: list[str] = []
            current_tokens = 0

            for para in paragraphs:
                para_tokens = estimate_tokens(para)

                # Atomic units: code blocks and tables
                if (_is_code_block(para) or _is_table(para)) and para_tokens <= chunk_size * 2:
                    # Flush current buffer first
                    if current_content:
                        chunks.append(self._make_chunk(
                            "\n\n".join(current_content), idx, heading,
                            page_number, source_type,
                        ))
                        idx += 1
                        current_content = []
                        current_tokens = 0
                    # Add the atomic block as its own chunk
                    chunks.append(self._make_chunk(
                        para, idx, heading, page_number, source_type,
                    ))
                    idx += 1
                    continue

                # If adding this paragraph exceeds chunk_size, flush
                if current_tokens + para_tokens > chunk_size and current_content:
                    chunks.append(self._make_chunk(
                        "\n\n".join(current_content), idx, heading,
                        page_number, source_type,
                    ))
                    idx += 1
                    # Overlap: keep last paragraph if it's small enough
                    if current_content and estimate_tokens(current_content[-1]) <= chunk_overlap:
                        current_content = [current_content[-1]]
                        current_tokens = estimate_tokens(current_content[0])
                    else:
                        current_content = []
                        current_tokens = 0

                # If a single paragraph is too large, split by sentences
                if para_tokens > chunk_size:
                    if current_content:
                        chunks.append(self._make_chunk(
                            "\n\n".join(current_content), idx, heading,
                            page_number, source_type,
                        ))
                        idx += 1
                        current_content = []
                        current_tokens = 0

                    sentence_chunks = _split_sentences(para, chunk_size)
                    for sc in sentence_chunks:
                        chunks.append(self._make_chunk(
                            sc, idx, heading, page_number, source_type,
                        ))
                        idx += 1
                    continue

                current_content.append(para)
                current_tokens += para_tokens

            # Flush remaining content for this section
            if current_content:
                chunks.append(self._make_chunk(
                    "\n\n".join(current_content), idx, heading,
                    page_number, source_type,
                ))
                idx += 1

        return chunks

    @staticmethod
    def _make_chunk(
        content: str, index: int, section: str | None,
        page_number: int | None, source_type: str | None,
    ) -> Chunk:
        return Chunk(
            chunk_index=index,
            content=content,
            token_count=estimate_tokens(content),
            page_number=page_number,
            section=section,
            source_type=source_type,
        )


def chunk_document(
    text: str,
    *,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    page_number: int | None = None,
    source_type: str | None = None,
) -> list[Chunk]:
    """Convenience function using the default SemanticChunker."""
    chunker = SemanticChunker()
    return chunker.chunk(
        text, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        page_number=page_number, source_type=source_type,
    )


def chunk_pages(
    pages: list[dict],
    *,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    source_type: str | None = None,
) -> list[Chunk]:
    """Chunk a list of pages (each with page_number and text), maintaining
    page-level metadata on each resulting chunk."""
    all_chunks: list[Chunk] = []
    global_idx = 0

    for page in pages:
        page_chunks = chunk_document(
            page["text"],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            page_number=page.get("page_number"),
            source_type=source_type,
        )
        for chunk in page_chunks:
            chunk.chunk_index = global_idx
            global_idx += 1
        all_chunks.extend(page_chunks)

    return all_chunks
