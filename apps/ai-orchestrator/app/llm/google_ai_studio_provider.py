"""Google AI Studio (Gemini API) — third provider tried in the
fallback_chain LLM provider (app/llm/provider_interface.py). Distinct from
GeminiProvider so the two can hold separate API keys/models — the existing
GeminiProvider remains the last-resort fallback."""
from __future__ import annotations

from google import genai
from google.genai import types

from app.core.config import settings


class GoogleAiStudioProvider:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.google_ai_studio_api_key)

    async def complete(self, *, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        response = await self._client.aio.models.generate_content(
            model=settings.google_ai_studio_model, contents=user_prompt, config=config,
        )
        return response.text or ""
