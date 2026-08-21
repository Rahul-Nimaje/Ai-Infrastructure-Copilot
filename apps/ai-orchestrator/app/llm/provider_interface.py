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
    if settings.llm_provider == "fallback_chain":
        from app.llm.fallback_provider import FallbackLlmProvider
        from app.llm.gemini_provider import GeminiProvider
        from app.llm.google_ai_studio_provider import GoogleAiStudioProvider
        from app.llm.nvidia_provider import NvidiaProvider
        from app.llm.openai_provider import OpenAiProvider
        from app.llm.openrouter_provider import OpenRouterProvider

        candidates: list[tuple[str, str, type]] = [
            ("openrouter", settings.openrouter_api_key, OpenRouterProvider),
            ("nvidia", settings.nvidia_api_key, NvidiaProvider),
            ("google_ai_studio", settings.google_ai_studio_api_key, GoogleAiStudioProvider),
            ("openai", settings.openai_api_key, OpenAiProvider),
            ("gemini", settings.gemini_api_key, GeminiProvider),
        ]
        providers = [(name, cls()) for name, api_key, cls in candidates if api_key]
        return FallbackLlmProvider(providers)
    raise NotImplementedError(f"LLM provider '{settings.llm_provider}' is not implemented in Phase 1.")
