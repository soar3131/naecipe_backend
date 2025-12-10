"""
통합 설정 모듈

모듈러 모놀리스 v2.0 - 단일 설정 파일로 모든 모듈 관리
"""

from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """통합 애플리케이션 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ==========================================================================
    # 애플리케이션 기본 설정
    # ==========================================================================
    APP_NAME: str = "naecipe-backend"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # ==========================================================================
    # 데이터베이스 설정 (단일 PostgreSQL, 스키마 분리)
    # ==========================================================================
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "naecipe"
    DATABASE_PASSWORD: SecretStr = SecretStr("naecipe_dev_password")
    DATABASE_NAME: str = "naecipe"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    @property
    def database_url(self) -> str:
        """비동기 PostgreSQL URL"""
        password = self.DATABASE_PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def database_url_sync(self) -> str:
        """동기 PostgreSQL URL (마이그레이션용)"""
        password = self.DATABASE_PASSWORD.get_secret_value()
        return (
            f"postgresql://{self.DATABASE_USER}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # ==========================================================================
    # Redis 설정 (단일 인스턴스)
    # ==========================================================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: SecretStr = SecretStr("")
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    @property
    def redis_url(self) -> str:
        """Redis URL"""
        password = self.REDIS_PASSWORD.get_secret_value()
        if password:
            return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ==========================================================================
    # JWT 설정
    # ==========================================================================
    JWT_SECRET_KEY: str = "your-super-secret-key-min-32-chars-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==========================================================================
    # 보안 설정
    # ==========================================================================
    PASSWORD_MIN_LENGTH: int = 8
    LOGIN_FAILURE_LIMIT: int = 5
    ACCOUNT_LOCK_MINUTES: int = 15

    # ==========================================================================
    # OAuth 설정
    # ==========================================================================
    # Kakao
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:3000/auth/callback/kakao"

    # Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback/google"

    # Naver
    NAVER_CLIENT_ID: str = ""
    NAVER_CLIENT_SECRET: str = ""
    NAVER_REDIRECT_URI: str = "http://localhost:3000/auth/callback/naver"

    OAUTH_STATE_EXPIRE_SECONDS: int = 600

    # ==========================================================================
    # 캐시 설정
    # ==========================================================================
    CACHE_DEFAULT_TTL: int = 300  # 5분
    CACHE_RECIPE_TTL: int = 3600  # 1시간
    CACHE_SEARCH_TTL: int = 300  # 5분
    CACHE_SESSION_TTL: int = 86400  # 24시간

    # ==========================================================================
    # AI Agent 설정 (예정)
    # ==========================================================================
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ==========================================================================
    # 헬퍼 프로퍼티
    # ==========================================================================
    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT.lower() == "development"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """프로덕션 환경에서 필수 설정 검증"""
        if self.is_production:
            if self.DEBUG:
                raise ValueError("프로덕션 환경에서는 DEBUG=False로 설정해야 합니다.")
            if self.JWT_SECRET_KEY == "your-super-secret-key-min-32-chars-change-in-production":
                raise ValueError("프로덕션 환경에서는 JWT_SECRET_KEY를 변경해야 합니다.")
        return self


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


settings = get_settings()
