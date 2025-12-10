"""
Recipes 모듈 Pydantic 스키마

레시피, 요리사, 검색 관련 스키마를 정의합니다.
"""

import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================================================
# 요리사 스키마
# ==========================================================================


class ChefSummary(BaseModel):
    """요리사 요약 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="요리사 이름")
    profile_image_url: str | None = Field(None, description="프로필 이미지 URL")
    specialty: str | None = Field(None, description="전문 분야")
    is_verified: bool = Field(default=False, description="인증 여부")


class ChefPlatformSchema(BaseModel):
    """요리사 플랫폼 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str = Field(description="플랫폼 종류")
    platform_id: str | None = Field(None, description="플랫폼 내 ID")
    platform_url: str | None = Field(None, description="플랫폼 URL")
    subscriber_count: int | None = Field(None, description="구독자 수")


class ChefListItem(BaseModel):
    """요리사 목록 아이템 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="요리사 이름")
    profile_image_url: str | None = Field(None, description="프로필 이미지 URL")
    specialty: str | None = Field(None, description="전문 분야")
    recipe_count: int = Field(description="등록된 레시피 수")
    is_verified: bool = Field(description="인증 여부")


class ChefDetail(BaseModel):
    """요리사 상세 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="요리사 이름")
    profile_image_url: str | None = Field(None, description="프로필 이미지 URL")
    bio: str | None = Field(None, description="요리사 소개")
    specialty: str | None = Field(None, description="전문 분야")

    # 통계
    recipe_count: int = Field(description="등록된 레시피 수")
    total_views: int = Field(description="총 조회수")
    avg_rating: float = Field(description="평균 평점")

    # 상태
    is_verified: bool = Field(description="인증 여부")

    # 플랫폼 정보
    platforms: list[ChefPlatformSchema] = Field(
        default_factory=list, description="플랫폼 목록"
    )

    # 메타 정보
    created_at: datetime = Field(description="생성 시각")
    updated_at: datetime = Field(description="수정 시각")


class ChefListResponse(BaseModel):
    """요리사 목록 응답 스키마"""

    items: list[ChefListItem] = Field(description="요리사 목록")
    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")
    total_count: int | None = Field(None, description="전체 개수")


# ==========================================================================
# 레시피 스키마
# ==========================================================================


class IngredientSchema(BaseModel):
    """재료 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="재료명")
    amount: str | None = Field(None, description="양")
    unit: str | None = Field(None, description="단위")
    note: str | None = Field(None, description="부가 설명")
    order_index: int = Field(description="표시 순서")


class CookingStepSchema(BaseModel):
    """조리 단계 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    step_number: int = Field(description="단계 번호")
    description: str = Field(description="단계 설명")
    image_url: str | None = Field(None, description="단계별 이미지 URL")
    duration_seconds: int | None = Field(None, description="소요 시간 (초)")
    tip: str | None = Field(None, description="조리 팁")


class TagSchema(BaseModel):
    """태그 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="태그명")
    category: str | None = Field(None, description="태그 카테고리")


class RecipeListItem(BaseModel):
    """레시피 목록 아이템 스키마 (간략)"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str = Field(description="레시피 제목")
    description: str | None = Field(None, description="레시피 설명")
    thumbnail_url: str | None = Field(None, description="썸네일 URL")
    prep_time_minutes: int | None = Field(None, description="준비 시간 (분)")
    cook_time_minutes: int | None = Field(None, description="조리 시간 (분)")
    difficulty: str | None = Field(None, description="난이도")
    exposure_score: float = Field(description="노출 점수")
    chef: ChefSummary | None = Field(None, description="요리사 정보")
    tags: list[TagSchema] = Field(default_factory=list, description="태그 목록")
    created_at: datetime = Field(description="생성 시각")


class RecipeDetail(BaseModel):
    """레시피 상세 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str = Field(description="레시피 제목")
    description: str | None = Field(None, description="레시피 설명")
    thumbnail_url: str | None = Field(None, description="썸네일 URL")
    video_url: str | None = Field(None, description="영상 URL")

    # 조리 정보
    prep_time_minutes: int | None = Field(None, description="준비 시간 (분)")
    cook_time_minutes: int | None = Field(None, description="조리 시간 (분)")
    total_time_minutes: int | None = Field(None, description="총 소요 시간 (분)")
    servings: int | None = Field(None, description="인분")
    difficulty: str | None = Field(None, description="난이도")

    # 출처 정보
    source_url: str | None = Field(None, description="원본 소스 URL")
    source_platform: str | None = Field(None, description="출처 플랫폼")

    # 통계
    exposure_score: float = Field(description="노출 점수")
    view_count: int = Field(description="조회수")

    # 관련 정보
    chef: ChefSummary | None = Field(None, description="요리사 정보")
    ingredients: list[IngredientSchema] = Field(
        default_factory=list, description="재료 목록"
    )
    steps: list[CookingStepSchema] = Field(
        default_factory=list, description="조리 단계"
    )
    tags: list[TagSchema] = Field(default_factory=list, description="태그 목록")

    # 메타 정보
    created_at: datetime = Field(description="생성 시각")
    updated_at: datetime = Field(description="수정 시각")

    @classmethod
    def from_model(cls, recipe: Any) -> "RecipeDetail":
        """모델에서 스키마 생성"""
        tags = [
            TagSchema.model_validate(rt.tag) for rt in recipe.recipe_tags if rt.tag
        ]

        return cls(
            id=recipe.id,
            title=recipe.title,
            description=recipe.description,
            thumbnail_url=recipe.thumbnail_url,
            video_url=recipe.video_url,
            prep_time_minutes=recipe.prep_time_minutes,
            cook_time_minutes=recipe.cook_time_minutes,
            total_time_minutes=recipe.total_time_minutes,
            servings=recipe.servings,
            difficulty=recipe.difficulty,
            source_url=recipe.source_url,
            source_platform=recipe.source_platform,
            exposure_score=recipe.exposure_score,
            view_count=recipe.view_count,
            chef=ChefSummary.model_validate(recipe.chef) if recipe.chef else None,
            ingredients=[
                IngredientSchema.model_validate(ing) for ing in recipe.ingredients
            ],
            steps=[CookingStepSchema.model_validate(step) for step in recipe.steps],
            tags=tags,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
        )


class RecipeListResponse(BaseModel):
    """레시피 목록 응답 스키마"""

    items: list[RecipeListItem] = Field(description="레시피 목록")
    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")
    total_count: int | None = Field(None, description="전체 개수")


# ==========================================================================
# 검색 스키마
# ==========================================================================


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


# ==========================================================================
# 페이지네이션 스키마
# ==========================================================================


class CursorData(BaseModel):
    """커서 내부 데이터"""

    id: str  # 마지막 아이템 ID
    created_at: datetime | None = None  # 정렬 기준 타임스탬프
    score: float | None = None  # 정렬 기준 점수 (인기도 등)


class PaginationParams(BaseModel):
    """페이지네이션 파라미터"""

    cursor: str | None = Field(None, description="페이지네이션 커서")
    limit: int = Field(20, ge=1, le=100, description="페이지당 항목 수")
