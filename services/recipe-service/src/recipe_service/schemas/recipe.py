"""
레시피 Pydantic 스키마

레시피 API 요청/응답 스키마를 정의합니다.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from recipe_service.schemas.chef import ChefSummary


# 재료 스키마
class IngredientSchema(BaseModel):
    """재료 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="재료명")
    amount: str | None = Field(None, description="양")
    unit: str | None = Field(None, description="단위")
    note: str | None = Field(None, description="부가 설명")
    order_index: int = Field(description="표시 순서")


# 조리 단계 스키마
class CookingStepSchema(BaseModel):
    """조리 단계 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    step_number: int = Field(description="단계 번호")
    description: str = Field(description="단계 설명")
    image_url: str | None = Field(None, description="단계별 이미지 URL")
    duration_seconds: int | None = Field(None, description="소요 시간 (초)")
    tip: str | None = Field(None, description="조리 팁")


# 태그 스키마
class TagSchema(BaseModel):
    """태그 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="태그명")
    category: str | None = Field(None, description="태그 카테고리")


# 레시피 목록 아이템 스키마 (간략 버전)
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


# 레시피 상세 스키마
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
    ingredients: list[IngredientSchema] = Field(default_factory=list, description="재료 목록")
    steps: list[CookingStepSchema] = Field(default_factory=list, description="조리 단계")
    tags: list[TagSchema] = Field(default_factory=list, description="태그 목록")

    # 메타 정보
    created_at: datetime = Field(description="생성 시각")
    updated_at: datetime = Field(description="수정 시각")

    @classmethod
    def from_model(cls, recipe: Any) -> "RecipeDetail":
        """모델에서 스키마 생성"""
        # tags 프로퍼티를 통해 태그 목록 가져오기
        tags = [
            TagSchema.model_validate(rt.tag)
            for rt in recipe.recipe_tags
            if rt.tag
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
            steps=[
                CookingStepSchema.model_validate(step) for step in recipe.steps
            ],
            tags=tags,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
        )


# 레시피 목록 응답 스키마
class RecipeListResponse(BaseModel):
    """레시피 목록 응답 스키마"""

    items: list[RecipeListItem] = Field(description="레시피 목록")
    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")
    total_count: int | None = Field(None, description="전체 개수")
