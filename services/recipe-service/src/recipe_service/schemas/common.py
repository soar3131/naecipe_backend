"""
공통 Pydantic 스키마

에러 응답, 페이지네이션 등 공통으로 사용되는 스키마를 정의합니다.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    """표준 에러 응답"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "RESOURCE_NOT_FOUND",
                "message": "레시피를 찾을 수 없습니다",
                "details": [],
            }
        }
    )

    code: str = Field(description="에러 코드")
    message: str = Field(description="에러 메시지")
    details: list[ErrorDetail] = Field(default_factory=list, description="상세 에러 정보")


class CursorInfo(BaseModel):
    """커서 페이지네이션 정보"""

    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션된 응답 기본 클래스"""

    items: list[T] = Field(description="아이템 목록")
    cursor: CursorInfo = Field(description="커서 정보")
    total_count: int | None = Field(None, description="전체 개수 (선택적)")


class HealthStatus(BaseModel):
    """헬스 체크 상태"""

    status: str = Field(description="상태 (healthy, unhealthy)")
    timestamp: datetime = Field(default_factory=datetime.now, description="체크 시각")
    details: dict[str, Any] = Field(default_factory=dict, description="상세 정보")


class BaseSchema(BaseModel):
    """기본 스키마 클래스"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
