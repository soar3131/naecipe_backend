"""
Recipe Service 설정

Pydantic Settings를 사용하여 환경 변수를 로드하고 검증합니다.
DatabaseSettings, RedisSettings, KafkaSettings로 분리하여 관리합니다.
"""

from functools import lru_cache
from typing import Any

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class Settings(BaseSettings):
    """애플리케이션 통합 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 서비스 정보
    SERVICE_NAME: str = "recipe-service"
    SERVICE_PORT: int = 8001
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # 분리된 설정 객체
    _database: DatabaseSettings | None = None
    _redis: RedisSettings | None = None
    _kafka: KafkaSettings | None = None

    @property
    def database(self) -> DatabaseSettings:
        """데이터베이스 설정"""
        if self._database is None:
            self._database = DatabaseSettings()
        return self._database

    @property
    def redis(self) -> RedisSettings:
        """Redis 설정"""
        if self._redis is None:
            self._redis = RedisSettings()
        return self._redis

    @property
    def kafka(self) -> KafkaSettings:
        """Kafka 설정"""
        if self._kafka is None:
            self._kafka = KafkaSettings()
        return self._kafka

    # 하위 호환성을 위한 프로퍼티
    @property
    def DATABASE_URL(self) -> str:
        """비동기 PostgreSQL URL (하위 호환성)"""
        return self.database.async_url

    @property
    def REDIS_URL(self) -> str:
        """Redis URL (하위 호환성)"""
        return self.redis.url

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
            # 프로덕션에서는 DEBUG가 False여야 함
            if self.DEBUG:
                raise ValueError("프로덕션 환경에서는 DEBUG=False로 설정해야 합니다.")
        return self


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


settings = get_settings()
