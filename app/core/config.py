from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "development-secret-key-replace-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/memoledger"
    READONLY_DATABASE_URL: str = "postgresql://readonly_agent:readonly_secret_password@localhost:5432/memoledger"

    # Celery & Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # S3 Object Storage
    S3_ENDPOINT: str = "localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "memoledger-memos"
    S3_USE_SSL: bool = False

    # Vision LLM Provider
    # Options: "gemini", "openai", "anthropic", "mock"
    VISION_LLM_PROVIDER: str = "mock"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Tracing & Cost Monitoring
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # App Defaults
    DEFAULT_CURRENCY: str = "BDT"
    TIMEZONE: str = "Asia/Dhaka"


settings = Settings()
