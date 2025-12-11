"""
Cookbooks 모듈 Pydantic 스키마

레시피북 API 요청/응답 스키마를 정의합니다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================================================
# 요청 스키마
# ==========================================================================


class CookbookCreateRequest(BaseModel):
    """레시피북 생성 요청"""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="레시피북 이름 (1-100자)",
        examples=["한식 모음"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="레시피북 설명 (최대 500자)",
        examples=["한식 레시피 모음집"],
    )
    cover_image_url: str | None = Field(
        default=None,
        max_length=500,
        description="커버 이미지 URL",
        examples=["https://example.com/images/cover.jpg"],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """이름 앞뒤 공백 제거"""
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """설명 앞뒤 공백 제거"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class CookbookUpdateRequest(BaseModel):
    """레시피북 수정 요청"""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="레시피북 이름 (1-100자)",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="레시피북 설명 (null로 삭제 가능)",
    )
    cover_image_url: str | None = Field(
        default=None,
        max_length=500,
        description="커버 이미지 URL (null로 삭제 가능)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """이름 앞뒤 공백 제거"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("이름은 비어있을 수 없습니다")
            return v
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """설명 앞뒤 공백 제거"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class CookbookReorderRequest(BaseModel):
    """레시피북 순서 변경 요청"""

    cookbook_ids: list[str] = Field(
        ...,
        min_length=1,
        description="원하는 순서대로 정렬된 레시피북 ID 목록",
        examples=[
            [
                "550e8400-e29b-41d4-a716-446655440001",
                "550e8400-e29b-41d4-a716-446655440002",
            ]
        ],
    )


# ==========================================================================
# 응답 스키마
# ==========================================================================


class CookbookResponse(BaseModel):
    """레시피북 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="레시피북 ID")
    name: str = Field(..., description="레시피북 이름")
    description: str | None = Field(None, description="레시피북 설명")
    cover_image_url: str | None = Field(None, description="커버 이미지 URL")
    sort_order: int = Field(..., description="정렬 순서")
    is_default: bool = Field(..., description="기본 레시피북 여부")
    saved_recipe_count: int = Field(default=0, description="저장된 레시피 수")
    created_at: datetime = Field(..., description="생성 시각")
    updated_at: datetime = Field(..., description="수정 시각")


class CookbookDetailResponse(CookbookResponse):
    """레시피북 상세 응답 (현재는 CookbookResponse와 동일)"""

    pass


class CookbookListResponse(BaseModel):
    """레시피북 목록 응답"""

    items: list[CookbookResponse] = Field(..., description="레시피북 목록")
    total: int = Field(..., description="전체 레시피북 수")


# ==========================================================================
# SavedRecipe 스키마 (SPEC-008)
# ==========================================================================


class SaveRecipeRequest(BaseModel):
    """레시피 저장 요청"""

    recipe_id: str = Field(
        ...,
        description="저장할 원본 레시피 ID",
        examples=["550e8400-e29b-41d4-a716-446655440001"],
    )
    memo: str | None = Field(
        default=None,
        max_length=1000,
        description="개인 메모 (최대 1000자)",
        examples=["백종원 레시피! 돼지고기 300g 필요"],
    )

    @field_validator("memo")
    @classmethod
    def validate_memo(cls, v: str | None) -> str | None:
        """메모 앞뒤 공백 제거"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class UpdateSavedRecipeRequest(BaseModel):
    """저장된 레시피 수정 요청 (메모 수정)"""

    memo: str | None = Field(
        default=None,
        max_length=1000,
        description="개인 메모 (최대 1000자, null로 삭제 가능)",
    )

    @field_validator("memo")
    @classmethod
    def validate_memo(cls, v: str | None) -> str | None:
        """메모 앞뒤 공백 제거"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return v


class RecipeSummary(BaseModel):
    """레시피 요약 정보 (저장된 레시피 목록용)"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="레시피 ID")
    title: str = Field(..., description="레시피 제목")
    thumbnail_url: str | None = Field(None, description="썸네일 URL")
    chef_name: str | None = Field(None, description="셰프 이름")


class SavedRecipeResponse(BaseModel):
    """저장된 레시피 응답"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="저장된 레시피 ID")
    cookbook_id: str = Field(..., description="레시피북 ID")
    recipe: RecipeSummary | None = Field(None, description="원본 레시피 정보")
    memo: str | None = Field(None, description="개인 메모")
    cook_count: int = Field(default=0, description="조리 횟수")
    personal_rating: float | None = Field(None, description="개인 평점 (0.0-5.0)")
    last_cooked_at: datetime | None = Field(None, description="마지막 조리 일시")
    created_at: datetime = Field(..., description="저장 시각")
    updated_at: datetime = Field(..., description="수정 시각")


class SavedRecipeDetailResponse(SavedRecipeResponse):
    """저장된 레시피 상세 응답 (원본 레시피 전체 정보 포함)"""

    # recipe 필드는 RecipeSummary 대신 상세 정보를 포함
    # 현재는 SavedRecipeResponse와 동일, 추후 RecipeDetail 스키마로 확장
    pass


class SavedRecipeListResponse(BaseModel):
    """저장된 레시피 목록 응답"""

    items: list[SavedRecipeResponse] = Field(..., description="저장된 레시피 목록")
    total: int = Field(..., description="전체 항목 수")
    limit: int = Field(..., description="페이지당 항목 수")
    offset: int = Field(..., description="건너뛴 항목 수")
