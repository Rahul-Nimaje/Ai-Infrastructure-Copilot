"""NVIDIA NIM — OpenAI-compatible chat completions API hosted at
integrate.api.nvidia.com. Second provider tried in the fallback_chain
LLM provider (app/llm/provider_interface.py)."""
from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaProvider:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.nvidia_api_key, base_url=NVIDIA_BASE_URL)

    async def complete(self, *, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        response = await self._client.chat.completions.create(
            model=settings.nvidia_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"} if json_mode else {"type": "text"},
        )
        return response.choices[0].message.content or ""
