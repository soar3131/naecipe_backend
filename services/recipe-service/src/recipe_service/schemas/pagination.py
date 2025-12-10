"""
커서 기반 페이지네이션 유틸리티

Base64 인코딩된 커서를 사용하여 효율적인 페이지네이션을 구현합니다.
"""

import base64
import json
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class CursorData(BaseModel):
    """커서 내부 데이터"""

    id: str  # 마지막 아이템 ID
    created_at: datetime | None = None  # 정렬 기준 타임스탬프
    score: float | None = None  # 정렬 기준 점수 (인기도 등)


class PaginationParams(BaseModel):
    """페이지네이션 파라미터"""

    cursor: str | None = Field(None, description="페이지네이션 커서")
    limit: int = Field(20, ge=1, le=100, description="페이지당 항목 수")


class CursorInfo(BaseModel):
    """커서 정보"""

    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션된 응답"""

    items: list[T] = Field(description="아이템 목록")
    cursor: CursorInfo = Field(description="커서 정보")
    total_count: int | None = Field(None, description="전체 개수 (선택적)")


def encode_cursor(data: CursorData) -> str:
    """커서 데이터를 Base64 문자열로 인코딩"""
    json_str = data.model_dump_json()
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor_str: str) -> CursorData | None:
    """Base64 커서 문자열을 CursorData로 디코딩"""
    try:
        json_str = base64.urlsafe_b64decode(cursor_str.encode()).decode()
        data = json.loads(json_str)
        return CursorData.model_validate(data)
    except Exception:
        return None


def create_next_cursor(
    items: list[Any],
    id_field: str = "id",
    timestamp_field: str | None = "created_at",
    score_field: str | None = None,
) -> str | None:
    """
    아이템 목록에서 다음 커서 생성

    Args:
        items: 아이템 목록
        id_field: ID 필드명
        timestamp_field: 타임스탬프 필드명
        score_field: 점수 필드명 (인기도 정렬용)

    Returns:
        인코딩된 커서 문자열 또는 None
    """
    if not items:
        return None

    last_item = items[-1]

    # 딕셔너리 또는 객체에서 값 추출
    def get_value(obj: Any, field: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    item_id = get_value(last_item, id_field)
    if item_id is None:
        return None

    # UUID를 문자열로 변환
    if isinstance(item_id, UUID):
        item_id = str(item_id)

    cursor_data = CursorData(
        id=item_id,
        created_at=get_value(last_item, timestamp_field) if timestamp_field else None,
        score=get_value(last_item, score_field) if score_field else None,
    )

    return encode_cursor(cursor_data)


def paginate_response(
    items: list[T],
    limit: int,
    id_field: str = "id",
    timestamp_field: str | None = "created_at",
    score_field: str | None = None,
    total_count: int | None = None,
) -> PaginatedResponse[T]:
    """
    페이지네이션된 응답 생성

    Args:
        items: 조회된 아이템 목록 (limit + 1개 조회 권장)
        limit: 요청된 limit
        id_field: ID 필드명
        timestamp_field: 타임스탬프 필드명
        score_field: 점수 필드명
        total_count: 전체 개수

    Returns:
        PaginatedResponse 객체
    """
    # limit + 1개를 조회했다면 다음 페이지 존재
    has_more = len(items) > limit
    result_items = items[:limit] if has_more else items

    next_cursor = None
    if has_more and result_items:
        next_cursor = create_next_cursor(
            result_items,
            id_field=id_field,
            timestamp_field=timestamp_field,
            score_field=score_field,
        )

    return PaginatedResponse(
        items=result_items,
        cursor=CursorInfo(next_cursor=next_cursor, has_more=has_more),
        total_count=total_count,
    )
