"""Text cleaning pipeline — normalizes whitespace, strips artifacts,
and prepares extracted text for chunking."""
from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """Apply all cleaning steps in sequence."""
    text = normalize_unicode(text)
    text = strip_control_characters(text)
    text = normalize_whitespace(text)
    text = strip_repeated_headers_footers(text)
    return text.strip()


def normalize_unicode(text: str) -> str:
    """Normalize unicode to NFC form for consistent matching."""
    return unicodedata.normalize("NFC", text)


def strip_control_characters(text: str) -> str:
    """Remove control characters except newlines and tabs."""
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)


def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines and trailing spaces while preserving
    intentional paragraph breaks."""
    # Replace tabs with spaces
    text = text.replace("\t", "    ")
    # Remove trailing whitespace per line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    # Collapse 3+ consecutive newlines to 2 (preserving paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def strip_repeated_headers_footers(text: str) -> str:
    """Heuristically remove repeated header/footer lines that appear on every
    page of a PDF (common artifact). Uses a simple frequency heuristic:
    if a short line appears more than 3 times, it's likely a header/footer."""
    lines = text.split("\n")
    if len(lines) < 20:
        return text

    # Count short line frequencies (likely headers/footers)
    short_line_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if 3 <= len(stripped) <= 80:
            short_line_counts[stripped] = short_line_counts.get(stripped, 0) + 1

    # Lines appearing more than 3 times are probably repeated headers/footers
    repeated = {line for line, count in short_line_counts.items() if count > 3}

    if not repeated:
        return text

    cleaned_lines = [line for line in lines if line.strip() not in repeated]
    return "\n".join(cleaned_lines)
