"""Configuration settings for User Service"""

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
    SERVICE_NAME: str = "user-service"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8002
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://naecipe:password@localhost:5432/naecipe_user"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Configuration
    JWT_SECRET_KEY: str = "your-super-secret-key-min-32-chars-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    PASSWORD_MIN_LENGTH: int = 8
    LOGIN_FAILURE_LIMIT: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    # CORS
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
