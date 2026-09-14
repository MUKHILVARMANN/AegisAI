"""
AegisAI — Application Configuration
All settings loaded from environment variables with sensible defaults.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ─── App ─────────────────────────────────────────────────────────────
    app_name: str = "AegisAI"
    secret_key: str = "change-me-in-production"
    cors_origins: list[str] = ["http://localhost:3000"]
    api_port: int = 8000
    debug: bool = False

    # ─── Database ────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://aegisai:aegisai_secret@localhost:5432/aegisai"
    database_url_sync: str = "postgresql+psycopg2://aegisai:aegisai_secret@localhost:5432/aegisai"

    # ─── Redis / Celery ──────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ─── MinIO ───────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "aegisai-documents"
    minio_secure: bool = False

    # ─── LLM ────────────────────────────────────────────────────────────
    llm_provider: str = "openai"       # "openai" | "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"

    # ─── Embeddings ──────────────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # ─── Retrieval ───────────────────────────────────────────────────────
    retrieval_top_n: int = 20          # candidates before reranking
    reranker_top_k: int = 5            # final evidence chunks
    bm25_weight: float = 0.4
    vector_weight: float = 0.6
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ─── Rate Limiting ───────────────────────────────────────────────────
    rate_limit_requests: int = 100
    rate_limit_window: int = 60        # seconds

    # ─── Chunking ────────────────────────────────────────────────────────
    child_chunk_size: int = 512        # tokens
    child_chunk_overlap: int = 64
    parent_chunk_size: int = 2048


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
