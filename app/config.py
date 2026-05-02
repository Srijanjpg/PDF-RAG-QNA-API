from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PDF RAG API"
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: Path = Path("uploads")

    nvidia_api_key: str = Field(default="", repr=False)
    openai_api_key: str = Field(default="", repr=False)
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"
    embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    embedding_dimensions: int = 1024
    generation_model: str = "openai/gpt-oss-120b"
    generation_temperature: float = 1.0
    generation_top_p: float = 1.0
    generation_max_tokens: int = 4096
    generation_stream: bool = True

    max_upload_mb: int = 25
    chunk_tokens: int = 320
    chunk_overlap_tokens: int = 50
    retrieval_top_k: int = 8
    retrieval_min_score: float = 0.20
    cache_ttl_seconds: int = 3600

    @property
    def llm_api_key(self) -> str:
        return self.nvidia_api_key or self.openai_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
