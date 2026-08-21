"""Fallback chain — tries each configured LLM provider in priority order,
moving to the next on any failure (auth error, rate limit, outage, timeout)
instead of failing the request outright."""
from __future__ import annotations

import logging

from app.llm.provider_interface import LlmProvider

logger = logging.getLogger(__name__)


class FallbackLlmProvider:
    def __init__(self, providers: list[tuple[str, LlmProvider]]) -> None:
        if not providers:
            raise ValueError("FallbackLlmProvider needs at least one configured provider.")
        self._providers = providers

    async def complete(self, *, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        last_error: Exception | None = None
        for name, provider in self._providers:
            try:
                return await provider.complete(
                    system_prompt=system_prompt, user_prompt=user_prompt, json_mode=json_mode,
                )
            except Exception as exc:
                logger.warning("LLM provider '%s' failed, trying next fallback", name, exc_info=exc)
                last_error = exc
        raise last_error
