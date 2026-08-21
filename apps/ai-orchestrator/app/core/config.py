from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://copilot:copilot@localhost:5432/copilot"
    api_base_url: str = "http://localhost:8000"

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # Design principle 1 in docs/06-ai-architecture.md: provider-agnostic LLM
    # layer — "openai" and "gemini" are both wired; see app/llm/provider_interface.py.
    llm_provider: str = "openai"


settings = Settings()
