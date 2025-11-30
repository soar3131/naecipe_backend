"""
공통 Response 스키마

모든 서비스에서 공유되는 기본 응답 스키마를 정의합니다.
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """기본 API 응답 스키마"""

    success: bool = True
    data: T | None = None
    message: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
