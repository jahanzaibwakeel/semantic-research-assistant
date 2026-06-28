from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Semantic Research Assistant"
    api_prefix: str = "/api"
    environment: str = "development"
    secret_key: str = Field(default="change-me-in-production")
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    rate_limit_backend: str = "memory"
    security_headers_enabled: bool = True
    content_security_policy: str = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
    )

    database_url: str = "postgresql+psycopg://research:research@postgres:5432/research"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "research_chunks"

    upload_dir: Path = Path("storage/uploads")
    max_upload_mb: int = 50
    storage_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str = "research-documents"
    s3_region: str = "us-east-1"
    file_scan_enabled: bool = False
    file_scan_command: str | None = None
    file_scan_timeout_seconds: int = 30
    ocr_enabled: bool = False
    ocr_min_text_chars: int = 200
    chunk_size: int = 1200
    chunk_overlap: int = 180
    keyword_candidate_limit: int = 80
    vector_candidate_multiplier: int = 4
    min_relevance_score: float = 0.05

    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1"
    llm_provider: str = "openai"

    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("embedding_provider", "llm_provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.lower().strip()

    @field_validator("rate_limit_backend", "storage_backend")
    @classmethod
    def normalize_backend(cls, value: str) -> str:
        return value.lower().strip()

    @model_validator(mode="after")
    def validate_settings(self):
        if self.environment == "production" and self.secret_key == "change-me-in-production":
            raise ValueError("SECRET_KEY must be changed in production")
        if self.max_upload_mb <= 0:
            raise ValueError("MAX_UPLOAD_MB must be greater than zero")
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be greater than zero")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be greater than or equal to zero and less than CHUNK_SIZE")
        if self.keyword_candidate_limit <= 0:
            raise ValueError("KEYWORD_CANDIDATE_LIMIT must be greater than zero")
        if self.vector_candidate_multiplier <= 0:
            raise ValueError("VECTOR_CANDIDATE_MULTIPLIER must be greater than zero")
        if self.rate_limit_backend not in {"memory", "redis"}:
            raise ValueError("RATE_LIMIT_BACKEND must be either 'memory' or 'redis'")
        if self.llm_provider not in {"openai", "ollama"}:
            raise ValueError("LLM_PROVIDER must be either 'openai' or 'ollama'")
        if self.embedding_provider not in {"openai", "sentence-transformers"}:
            raise ValueError("EMBEDDING_PROVIDER must be either 'openai' or 'sentence-transformers'")
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("STORAGE_BACKEND must be either 'local' or 's3'")
        if self.file_scan_enabled and not self.file_scan_command:
            raise ValueError("FILE_SCAN_COMMAND must be set when FILE_SCAN_ENABLED is true")
        if self.file_scan_timeout_seconds <= 0:
            raise ValueError("FILE_SCAN_TIMEOUT_SECONDS must be greater than zero")
        return self


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
