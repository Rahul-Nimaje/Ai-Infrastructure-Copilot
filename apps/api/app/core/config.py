from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://copilot:copilot@localhost:5434/copilot"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_access_token_ttl_seconds: int = 60 * 60 * 24 * 7
    jwt_refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30

    # MVP simplification #3 (plan): local envelope encryption instead of HashiCorp Vault.
    local_vault_master_key: str = "dev-local-vault-master-key-change-me-32bytes"

    # MVP simplification #1/#2 (plan): execution is feature-flagged off by default,
    # and gated per-organization on top of this global switch.
    execution_enabled: bool = False

    ai_orchestrator_url: str = "http://localhost:8001"

    cors_origins: list[str] = ["http://localhost:3000"]

    # ── Network Discovery / Full Inventory Scan ────────────────────────
    # Caps simultaneous WinRM/SSH/SNMP connections per organization during a
    # Full scan's credentialed collection phase (section 11/16 of the
    # feature plan) — protects the target fleet, independent of Celery's
    # own worker-level concurrency which protects this server's resources.
    discovery_max_concurrent_inventory: int = 5

    # ── RAG / Knowledge Base ────────────────────────────────────────────
    embedding_provider: str = "openai"  # openai | local
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Chunking
    chunk_size: int = 512  # target tokens per chunk
    chunk_overlap: int = 50  # overlap tokens between chunks

    # Retrieval
    rag_initial_top_k: int = 20
    rag_final_top_k: int = 6

    # File upload
    max_upload_size_mb: int = 50
    allowed_file_types: list[str] = [
        "pdf", "docx", "txt", "md", "csv", "html", "ps1", "sh",
    ]

    # Storage
    file_storage_backend: str = "local"  # local | s3
    file_storage_path: str = "./storage/documents"
    s3_bucket: str = ""
    s3_region: str = ""


settings = Settings()

