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
