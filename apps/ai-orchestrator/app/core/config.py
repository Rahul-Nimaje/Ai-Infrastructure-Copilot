from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://copilot:copilot@localhost:5434/copilot"
    api_base_url: str = "http://localhost:8000"

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    nvidia_api_key: str = ""
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    google_ai_studio_api_key: str = ""
    google_ai_studio_model: str = "gemini-2.0-flash-001"

    # Design principle 1 in docs/06-ai-architecture.md: provider-agnostic LLM
    # layer — see app/llm/provider_interface.py. "fallback_chain" tries
    # OpenRouter -> NVIDIA NIM -> Google AI Studio -> OpenAI -> Gemini in
    # order, skipping any provider whose API key isn't configured, and
    # moving to the next provider on failure rather than erroring out.
    llm_provider: str = "fallback_chain"

    # ── RAG retrieval (must match apps/api's ingestion-side config so query
    # embeddings land in the same vector space as the stored chunk embeddings) ──
    embedding_provider: str = "openai"  # openai | local
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536


settings = Settings()
