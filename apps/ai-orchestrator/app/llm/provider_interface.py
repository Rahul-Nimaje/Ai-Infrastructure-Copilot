"""Provider-agnostic LLM interface — docs/06-ai-architecture.md Section 1,
design principle 1: agents call this interface, never an SDK directly, so
swapping providers never touches agent logic. OpenAI and Gemini are both
wired for Phase 1; a LocalModelProvider satisfying the same Protocol is
Phase 2+ (no exit criterion needs it yet)."""
from __future__ import annotations

from typing import Protocol


class LlmProvider(Protocol):
    async def complete(self, *, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Returns the model's text completion (or a JSON string if json_mode)."""
        ...


def get_llm_provider() -> LlmProvider:
    from app.core.config import settings

    if settings.llm_provider == "openai":
        from app.llm.openai_provider import OpenAiProvider

        return OpenAiProvider()
    if settings.llm_provider == "gemini":
        from app.llm.gemini_provider import GeminiProvider

        return GeminiProvider()
    raise NotImplementedError(f"LLM provider '{settings.llm_provider}' is not implemented in Phase 1.")
