import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

# The `-latest` alias routes a disproportionate share of free-tier traffic
# and returns 503 UNAVAILABLE under load far more often than pinned model
# versions; some older model ids (e.g. gemini-2.5-flash, gemini-2.5-flash-lite)
# also 404 as "no longer available to new users" depending on the key's
# project. Configured model tried first; these are tried in order on any
# API-level failure before giving up, so one model's overload/deprecation
# doesn't fail the whole request.
_FALLBACK_MODELS = ["gemini-2.0-flash-001", "gemini-flash-lite-latest", "gemini-2.0-flash-lite-001"]


class GeminiProvider:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def complete(self, *, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        models_to_try = [settings.gemini_model] + [m for m in _FALLBACK_MODELS if m != settings.gemini_model]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        last_error: Exception | None = None
        for model in models_to_try:
            try:
                response = await self._client.aio.models.generate_content(
                    model=model, contents=user_prompt, config=config
                )
                return response.text or ""
            except genai_errors.APIError as exc:
                # Covers both ServerError (503 overload) and ClientError
                # (404 model deprecated/unavailable for this key) — either
                # way, the right move is to try the next candidate model.
                logger.warning("Gemini model '%s' unavailable (%s), trying next fallback", model, exc)
                last_error = exc
                continue
        raise last_error
