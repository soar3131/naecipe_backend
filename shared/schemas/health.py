"""
헬스체크 스키마

모든 서비스에서 공유되는 헬스체크 응답 스키마를 정의합니다.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness 응답 스키마"""

    status: Literal["healthy"] = "healthy"
    service: str
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DependencyChecks(BaseModel):
    """의존 서비스 상태"""

    database: bool = False
    redis: bool = False
    kafka: bool = False
    elasticsearch: bool | None = None  # search-service 전용


class ReadinessResponse(BaseModel):
    """Readiness 응답 스키마"""

    status: Literal["ready", "not_ready"]
    service: str
    checks: DependencyChecks
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
