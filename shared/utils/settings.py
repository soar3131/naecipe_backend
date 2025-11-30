"""
공통 설정 베이스 클래스

모든 서비스에서 공유되는 Pydantic Settings 베이스 클래스입니다.
"""

from functools import lru_cache
from typing import Any

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """
    서비스 공통 설정 베이스 클래스

    모든 서비스 설정에서 상속받아 사용합니다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 서비스 정보
    SERVICE_NAME: str = "unknown-service"
    SERVICE_PORT: int = 8000
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT.lower() == "development"


class DatabaseSettings(BaseSettings):
    """데이터베이스 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "naecipe"
    DATABASE_PASSWORD: SecretStr = SecretStr("naecipe_dev_password")
    DATABASE_NAME: str = "naecipe"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    @property
    def async_url(self) -> str:
        """비동기 PostgreSQL URL"""
        password = self.DATABASE_PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def sync_url(self) -> str:
        """동기 PostgreSQL URL (마이그레이션용)"""
        password = self.DATABASE_PASSWORD.get_secret_value()
        return (
            f"postgresql://{self.DATABASE_USER}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


class RedisSettings(BaseSettings):
    """Redis 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: SecretStr = SecretStr("")
    REDIS_DB: int = 0

    @property
    def url(self) -> str:
        """Redis URL"""
        password = self.REDIS_PASSWORD.get_secret_value()
        if password:
            return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


class KafkaSettings(BaseSettings):
    """Kafka 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP_PREFIX: str = "naecipe"

    @property
    def bootstrap_servers_list(self) -> list[str]:
        """부트스트랩 서버 목록"""
        return [s.strip() for s in self.KAFKA_BOOTSTRAP_SERVERS.split(",")]


def validate_required_settings(
    settings: BaseSettings,
    required_fields: list[str],
) -> None:
    """
    필수 설정 검증

    Args:
        settings: 설정 인스턴스
        required_fields: 필수 필드 목록

    Raises:
        ValueError: 필수 필드가 누락된 경우
    """
    missing = []
    for field in required_fields:
        value = getattr(settings, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    if missing:
        raise ValueError(
            f"필수 환경 변수가 누락되었습니다: {', '.join(missing)}. "
            f".env 파일 또는 환경 변수를 확인해주세요."
        )
