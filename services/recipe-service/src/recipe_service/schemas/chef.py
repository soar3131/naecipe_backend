"""
요리사 Pydantic 스키마

요리사 API 요청/응답 스키마를 정의합니다.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# 요리사 요약 스키마 (레시피 응답에 포함)
class ChefSummary(BaseModel):
    """요리사 요약 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="요리사 이름")
    profile_image_url: str | None = Field(None, description="프로필 이미지 URL")
    specialty: str | None = Field(None, description="전문 분야")
    is_verified: bool = Field(description="인증 여부")


# 플랫폼 스키마
class ChefPlatformSchema(BaseModel):
    """요리사 플랫폼 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str = Field(description="플랫폼 종류")
    platform_id: str | None = Field(None, description="플랫폼 내 ID")
    platform_url: str | None = Field(None, description="플랫폼 URL")
    subscriber_count: int | None = Field(None, description="구독자 수")


# 요리사 목록 아이템 스키마
class ChefListItem(BaseModel):
    """요리사 목록 아이템 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(description="요리사 이름")
    profile_image_url: str | None = Field(None, description="프로필 이미지 URL")
    specialty: str | None = Field(None, description="전문 분야")
    recipe_count: int = Field(description="등록된 레시피 수")
    is_verified: bool = Field(description="인증 여부")


# 요리사 상세 스키마
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
        default_factory=list,
        description="플랫폼 목록"
    )

    # 메타 정보
    created_at: datetime = Field(description="생성 시각")
    updated_at: datetime = Field(description="수정 시각")


# 요리사 목록 응답 스키마
class ChefListResponse(BaseModel):
    """요리사 목록 응답 스키마"""

    items: list[ChefListItem] = Field(description="요리사 목록")
    next_cursor: str | None = Field(None, description="다음 페이지 커서")
    has_more: bool = Field(description="추가 페이지 존재 여부")
    total_count: int | None = Field(None, description="전체 개수")
