"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """App settings loaded from environment."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # App
    app_name: str = "DocIntelRAG"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/docintelrag"
    
    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3-coder"
    ollama_embed_model: str = "nomic-embed-text"
    
    # OCR
    ocr_timeout_seconds: int = 60
    ocr_dpi: int = 400
    
    # Ingestion
    allowed_upload_paths: list[str] = []
    max_file_size_mb: int = 100
    
    # Auth
    access_token_expire_minutes: int = 60 * 24  # 24 hours


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
