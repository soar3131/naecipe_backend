"""
검색 Pydantic 스키마

레시피 검색 API 요청/응답 스키마를 정의합니다.
"""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SearchQueryParams(BaseModel):
    """검색 API 요청 파라미터"""

    q: str | None = Field(
        default=None,
        max_length=100,
        description="검색 키워드 (제목, 설명, 재료명, 요리사명)",
    )
    difficulty: Literal["easy", "medium", "hard"] | None = Field(
        default=None,
        description="난이도 필터",
    )
    max_cook_time: int | None = Field(
        default=None,
        ge=1,
        le=1440,
        description="최대 조리시간 (분)",
    )
    tag: str | None = Field(
        default=None,
        max_length=50,
        description="태그 필터",
    )
    chef_id: UUID | None = Field(
        default=None,
        description="요리사 ID 필터",
    )
    sort: Literal["relevance", "latest", "cook_time", "popularity"] = Field(
        default="relevance",
        description="정렬 기준",
    )
    cursor: str | None = Field(
        default=None,
        max_length=200,
        description="페이지네이션 커서",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="결과 개수",
    )

    @field_validator("q")
    @classmethod
    def sanitize_keyword(cls, v: str | None) -> str | None:
        """검색어 정규화 및 검증"""
        if v is None:
            return None
        # 연속 공백 제거, 앞뒤 공백 제거
        v = re.sub(r"\s+", " ", v.strip())
        # 빈 문자열이면 None 반환
        return v if v else None


class ChefSummary(BaseModel):
    """검색 결과에 포함되는 요리사 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    profile_image_url: str | None = None


class TagSummary(BaseModel):
    """검색 결과에 포함되는 태그 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str | None = None


class SearchResultItem(BaseModel):
    """검색 결과 레시피 아이템"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    difficulty: str | None = None
    exposure_score: float
    chef: ChefSummary | None = None
    tags: list[TagSummary] = Field(default_factory=list)
    created_at: datetime


class SearchResult(BaseModel):
    """검색 API 응답"""

    items: list[SearchResultItem]
    next_cursor: str | None = None
    has_more: bool = False
    total_count: None = None  # 항상 null (성능 최적화)
