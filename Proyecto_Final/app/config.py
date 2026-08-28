from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    pinecone_api_key: SecretStr | None = None
    pinecone_index_name: str = "technical-documents"
    pinecone_namespace: str = "redshift-intelligence-v2"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    rag_top_k_dense: int = Field(default=8, ge=1, le=50)
    rag_top_k_sparse: int = Field(default=8, ge=1, le=50)
    rag_top_k_final: int = Field(default=5, ge=1, le=20)

    groq_api_key: SecretStr | None = None
    llm_model: str = "openai/gpt-oss-20b"

    redis_url: str = "redis://localhost:6379"
    job_ttl_seconds: int = Field(default=604800, ge=60)
    worker_concurrency: int = Field(default=2, ge=1, le=32)

    phoenix_enabled: bool = True
    phoenix_collector_endpoint: str = "http://localhost:6006/v1/traces"
    phoenix_project_name: str = "redshift-intelligence"

    documents_dir: Path = PROJECT_ROOT / "data" / "documents"

    @model_validator(mode="after")
    def validate_retrieval_limits(self) -> "Settings":
        if self.rag_top_k_final > self.rag_top_k_dense + self.rag_top_k_sparse:
            raise ValueError("RAG_TOP_K_FINAL cannot exceed all retrieval candidates")
        return self

    def require_external_services(self) -> None:
        missing = []
        if self.pinecone_api_key is None:
            missing.append("PINECONE_API_KEY")
        if self.groq_api_key is None:
            missing.append("GROQ_API_KEY")
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
