"""
헬스체크 API 엔드포인트

Kubernetes liveness/readiness probe에서 사용됩니다.
"""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from recipe_service.core.config import settings

router = APIRouter()


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


class ReadinessResponse(BaseModel):
    """Readiness 응답 스키마"""

    status: Literal["ready", "not_ready"]
    service: str
    checks: DependencyChecks
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    서비스 생존 확인 (Liveness)

    서비스가 실행 중인지 확인합니다.
    의존 서비스(DB, Redis 등) 상태와 무관하게 서비스 프로세스의 생존 여부만 확인합니다.
    """
    return HealthResponse(
        status="healthy",
        service=settings.SERVICE_NAME,
        version="1.0.0",
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(response: Response) -> ReadinessResponse:
    """
    서비스 준비 상태 확인 (Readiness)

    서비스가 트래픽을 처리할 준비가 되었는지 확인합니다.
    의존 서비스(DB, Redis 등) 연결 상태를 확인합니다.
    """
    checks = DependencyChecks()

    # TODO: 실제 연결 상태 확인 로직 구현
    # 현재는 개발 환경에서 true로 설정
    checks.database = True
    checks.redis = True
    checks.kafka = True

    all_ready = all([checks.database, checks.redis, checks.kafka])
    status_value: Literal["ready", "not_ready"] = "ready" if all_ready else "not_ready"

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=status_value,
        service=settings.SERVICE_NAME,
        checks=checks,
    )
