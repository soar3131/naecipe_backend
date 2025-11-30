"""Configuration settings for Ingestion Service"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Service Configuration
    SERVICE_NAME: str = "ingestion-service"
    PORT: int = 8009
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ingestion_service"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"


settings = Settings()
