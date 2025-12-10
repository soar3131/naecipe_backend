"""
공통 스키마

모든 모듈에서 공유되는 기본 응답 스키마를 정의합니다.
"""

from datetime import datetime, timezone
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ==========================================================================
# 기본 응답 스키마
# ==========================================================================


class BaseResponse(BaseModel, Generic[T]):
    """기본 API 응답 스키마"""

    success: bool = True
    data: T | None = None
    message: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    field: str | None = None
    message: str
    code: str | None = None


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""

    success: bool = False
    error: str
    details: list[ErrorDetail] | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답 스키마"""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @property
    def has_next(self) -> bool:
        """다음 페이지 존재 여부"""
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        """이전 페이지 존재 여부"""
        return self.page > 1


# ==========================================================================
# 헬스체크 스키마
# ==========================================================================


class HealthResponse(BaseModel):
    """Liveness 응답 스키마"""

    status: Literal["healthy"] = "healthy"
    service: str
    version: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DependencyChecks(BaseModel):
    """의존 서비스 상태"""

    database: bool = False
    redis: bool = False


class ReadinessResponse(BaseModel):
    """Readiness 응답 스키마"""

    status: Literal["ready", "not_ready"]
    service: str
    checks: DependencyChecks
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
