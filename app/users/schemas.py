"""
Users 모듈 Pydantic 스키마

인증, 사용자, 프로필, 취향 설정 관련 스키마를 정의합니다.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings


# ==========================================================================
# Enums
# ==========================================================================


class DietaryRestriction(str, Enum):
    """식이 제한 유형"""

    VEGETARIAN = "vegetarian"  # 채식 (유제품/계란 허용)
    VEGAN = "vegan"  # 비건 (동물성 제품 불가)
    PESCATARIAN = "pescatarian"  # 페스코 (해산물 허용)
    HALAL = "halal"  # 할랄
    KOSHER = "kosher"  # 코셔
    GLUTEN_FREE = "gluten_free"  # 글루텐 프리
    LACTOSE_FREE = "lactose_free"  # 유당 불내증
    LOW_SODIUM = "low_sodium"  # 저염식
    LOW_SUGAR = "low_sugar"  # 저당식


class Allergy(str, Enum):
    """알레르기 유형"""

    PEANUT = "peanut"  # 땅콩
    TREE_NUT = "tree_nut"  # 견과류
    MILK = "milk"  # 우유
    EGG = "egg"  # 달걀
    WHEAT = "wheat"  # 밀
    SOY = "soy"  # 대두
    FISH = "fish"  # 생선
    SHELLFISH = "shellfish"  # 갑각류/조개류
    SESAME = "sesame"  # 참깨


class CuisineCategory(str, Enum):
    """요리 카테고리"""

    KOREAN = "korean"  # 한식
    JAPANESE = "japanese"  # 일식
    CHINESE = "chinese"  # 중식
    WESTERN = "western"  # 양식
    ITALIAN = "italian"  # 이탈리안
    MEXICAN = "mexican"  # 멕시칸
    THAI = "thai"  # 태국
    VIETNAMESE = "vietnamese"  # 베트남
    INDIAN = "indian"  # 인도
    FUSION = "fusion"  # 퓨전


class OAuthProviderEnum(str, Enum):
    """OAuth 제공자 유형"""

    KAKAO = "kakao"
    GOOGLE = "google"
    NAVER = "naver"


# 프론트엔드 표시용 라벨 매핑
DIETARY_RESTRICTION_LABELS = {
    DietaryRestriction.VEGETARIAN: "채식 (유제품/계란 허용)",
    DietaryRestriction.VEGAN: "비건 (동물성 제품 불가)",
    DietaryRestriction.PESCATARIAN: "페스코 (해산물 허용)",
    DietaryRestriction.HALAL: "할랄",
    DietaryRestriction.KOSHER: "코셔",
    DietaryRestriction.GLUTEN_FREE: "글루텐 프리",
    DietaryRestriction.LACTOSE_FREE: "유당 불내증",
    DietaryRestriction.LOW_SODIUM: "저염식",
    DietaryRestriction.LOW_SUGAR: "저당식",
}

ALLERGY_LABELS = {
    Allergy.PEANUT: "땅콩",
    Allergy.TREE_NUT: "견과류",
    Allergy.MILK: "우유",
    Allergy.EGG: "달걀",
    Allergy.WHEAT: "밀",
    Allergy.SOY: "대두",
    Allergy.FISH: "생선",
    Allergy.SHELLFISH: "갑각류/조개류",
    Allergy.SESAME: "참깨",
}

CUISINE_CATEGORY_LABELS = {
    CuisineCategory.KOREAN: "한식",
    CuisineCategory.JAPANESE: "일식",
    CuisineCategory.CHINESE: "중식",
    CuisineCategory.WESTERN: "양식",
    CuisineCategory.ITALIAN: "이탈리안",
    CuisineCategory.MEXICAN: "멕시칸",
    CuisineCategory.THAI: "태국",
    CuisineCategory.VIETNAMESE: "베트남",
    CuisineCategory.INDIAN: "인도",
    CuisineCategory.FUSION: "퓨전",
}


# ==========================================================================
# 인증 스키마
# ==========================================================================


class RegisterRequest(BaseModel):
    """회원가입 요청 스키마"""

    email: EmailStr = Field(..., max_length=255, description="사용자 이메일 주소")
    password: str = Field(
        ...,
        min_length=settings.PASSWORD_MIN_LENGTH,
        max_length=128,
        description="비밀번호 (최소 8자, 영문+숫자 포함)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_policy(cls, v: str) -> str:
        """비밀번호 정책 검증"""
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"비밀번호는 최소 {settings.PASSWORD_MIN_LENGTH}자 이상이어야 합니다."
            )

        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("비밀번호는 최소 1개의 영문자를 포함해야 합니다.")

        if not re.search(r"\d", v):
            raise ValueError("비밀번호는 최소 1개의 숫자를 포함해야 합니다.")

        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """이메일 정규화 (소문자)"""
        return v.lower().strip()


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""

    email: EmailStr = Field(..., description="사용자 이메일 주소")
    password: str = Field(..., description="비밀번호")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """이메일 정규화 (소문자)"""
        return v.lower().strip()


class TokenResponse(BaseModel):
    """토큰 발급 응답 스키마"""

    access_token: str = Field(..., description="JWT Access Token (유효기간 15분)")
    refresh_token: str = Field(..., description="JWT Refresh Token (유효기간 7일)")
    token_type: Literal["bearer"] = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="Access Token 만료까지 남은 시간 (초)")


class RefreshRequest(BaseModel):
    """토큰 갱신 요청 스키마"""

    refresh_token: str = Field(..., description="Refresh Token")


# ==========================================================================
# 사용자 스키마
# ==========================================================================


class RegisterResponse(BaseModel):
    """회원가입 응답 스키마"""

    id: str = Field(..., description="생성된 사용자 ID")
    email: EmailStr = Field(..., description="등록된 이메일 주소")
    created_at: datetime = Field(..., description="계정 생성 시각")


class UserResponse(BaseModel):
    """사용자 정보 응답 스키마"""

    id: str = Field(..., description="사용자 ID")
    email: EmailStr = Field(..., description="이메일 주소")
    status: Literal["ACTIVE", "INACTIVE", "LOCKED"] = Field(
        ..., description="계정 상태"
    )
    created_at: datetime = Field(..., description="계정 생성 시각")

    model_config = {"from_attributes": True}


class UserInDB(BaseModel):
    """데이터베이스 사용자 모델 (내부 사용)"""

    id: str
    email: str
    password_hash: str
    status: str
    created_at: datetime
    updated_at: datetime
    locked_until: datetime | None = None

    model_config = {"from_attributes": True}


# ==========================================================================
# 프로필 스키마
# ==========================================================================


class ProfileUpdateRequest(BaseModel):
    """프로필 수정 요청 스키마"""

    display_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="표시 이름 (1-50자)",
        alias="displayName",
        examples=["홍길동"],
    )
    profile_image_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="프로필 이미지 URL",
        alias="profileImageUrl",
        examples=["https://cdn.naecipe.com/profiles/user123.jpg"],
    )

    @field_validator("profile_image_url")
    @classmethod
    def validate_url_format(cls, v: Optional[str]) -> Optional[str]:
        """URL 형식 검증"""
        if v is None:
            return v
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("유효한 URL 형식이 아닙니다 (http/https)")
        return v

    class Config:
        populate_by_name = True


class ProfileData(BaseModel):
    """프로필 데이터 응답"""

    id: str = Field(..., description="사용자 ID")
    email: str = Field(..., description="이메일 주소")
    display_name: str = Field(..., description="표시 이름", alias="displayName")
    profile_image_url: Optional[str] = Field(
        None, description="프로필 이미지 URL", alias="profileImageUrl"
    )
    created_at: datetime = Field(..., description="계정 생성 시각", alias="createdAt")
    updated_at: datetime = Field(
        ..., description="프로필 수정 시각", alias="updatedAt"
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class ProfileResponse(BaseModel):
    """프로필 API 응답"""

    success: bool = True
    data: ProfileData


# ==========================================================================
# 취향 설정 스키마
# ==========================================================================


class TasteValues(BaseModel):
    """맛 취향 값 (1-5 스케일)"""

    sweetness: Optional[int] = Field(None, ge=1, le=5, description="단맛 선호도 (1-5)")
    saltiness: Optional[int] = Field(None, ge=1, le=5, description="짠맛 선호도 (1-5)")
    spiciness: Optional[int] = Field(
        None, ge=1, le=5, description="매운맛 선호도 (1-5)"
    )
    sourness: Optional[int] = Field(None, ge=1, le=5, description="신맛 선호도 (1-5)")


class PreferencesUpdateRequest(BaseModel):
    """취향 설정 수정 요청 스키마"""

    dietary_restrictions: Optional[List[DietaryRestriction]] = Field(
        None, description="식이 제한 목록", alias="dietaryRestrictions"
    )
    allergies: Optional[List[Allergy]] = Field(None, description="알레르기 목록")
    cuisine_preferences: Optional[List[CuisineCategory]] = Field(
        None,
        max_length=10,
        description="선호 요리 카테고리 목록 (최대 10개)",
        alias="cuisinePreferences",
    )
    skill_level: Optional[int] = Field(
        None, ge=1, le=5, description="요리 실력 수준 (1-5)", alias="skillLevel"
    )
    household_size: Optional[int] = Field(
        None, ge=1, le=20, description="가구 인원 수 (1-20)", alias="householdSize"
    )
    taste_preferences: Optional[Dict[str, TasteValues]] = Field(
        None,
        description="맛 취향 (overall 또는 카테고리별)",
        alias="tastePreferences",
    )

    @field_validator("cuisine_preferences")
    @classmethod
    def validate_cuisine_preferences_count(
        cls, v: Optional[List[CuisineCategory]]
    ) -> Optional[List[CuisineCategory]]:
        """선호 요리 카테고리 최대 10개 제한"""
        if v is not None and len(v) > 10:
            raise ValueError("선호 요리 카테고리는 최대 10개까지 설정 가능합니다")
        return v

    @field_validator("taste_preferences")
    @classmethod
    def validate_taste_preference_keys(
        cls, v: Optional[Dict[str, TasteValues]]
    ) -> Optional[Dict[str, TasteValues]]:
        """맛 취향 키 검증"""
        if v is None:
            return v
        valid_keys = {"overall"} | {c.value for c in CuisineCategory}
        for key in v.keys():
            if key not in valid_keys:
                raise ValueError(f"허용되지 않는 카테고리입니다: {key}")
        return v

    class Config:
        populate_by_name = True


class TastePreferenceData(BaseModel):
    """맛 취향 응답 데이터"""

    sweetness: int = Field(..., description="단맛 선호도 (1-5)")
    saltiness: int = Field(..., description="짠맛 선호도 (1-5)")
    spiciness: int = Field(..., description="매운맛 선호도 (1-5)")
    sourness: int = Field(..., description="신맛 선호도 (1-5)")


class PreferencesData(BaseModel):
    """취향 설정 응답 데이터"""

    dietary_restrictions: List[str] = Field(
        default_factory=list, description="식이 제한 목록", alias="dietaryRestrictions"
    )
    allergies: List[str] = Field(default_factory=list, description="알레르기 목록")
    cuisine_preferences: List[str] = Field(
        default_factory=list,
        description="선호 요리 카테고리 목록",
        alias="cuisinePreferences",
    )
    skill_level: Optional[int] = Field(
        None, description="요리 실력 수준 (1-5)", alias="skillLevel"
    )
    household_size: Optional[int] = Field(
        None, description="가구 인원 수 (1-20)", alias="householdSize"
    )
    taste_preferences: Dict[str, TastePreferenceData] = Field(
        default_factory=dict, description="맛 취향", alias="tastePreferences"
    )
    updated_at: Optional[datetime] = Field(
        None, description="취향 설정 수정 시각", alias="updatedAt"
    )

    class Config:
        populate_by_name = True
        from_attributes = True


class PreferencesResponse(BaseModel):
    """취향 설정 API 응답"""

    success: bool = True
    data: PreferencesData


class OptionItem(BaseModel):
    """옵션 항목"""

    value: str = Field(..., description="API에서 사용하는 값")
    label: str = Field(..., description="사용자에게 표시할 라벨")


class OptionsResponse(BaseModel):
    """옵션 목록 API 응답"""

    success: bool = True
    data: List[OptionItem]


# ==========================================================================
# OAuth 스키마
# ==========================================================================


class OAuthCallbackRequest(BaseModel):
    """OAuth 콜백 요청 스키마"""

    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="CSRF 방지용 state 토큰")


class OAuthAuthorizationResponse(BaseModel):
    """OAuth 인가 URL 응답 스키마"""

    authorization_url: str = Field(..., description="소셜 로그인 페이지 URL")
    state: str = Field(..., description="CSRF 방지용 state 토큰")


class OAuthUserInfo(BaseModel):
    """OAuth 사용자 정보 응답 스키마"""

    id: str = Field(..., description="사용자 ID")
    email: str = Field(..., description="이메일 주소")
    provider: OAuthProviderEnum = Field(..., description="OAuth 제공자")
    created_at: datetime | None = Field(None, description="계정 생성 시각")


class OAuthLoginResponse(BaseModel):
    """OAuth 로그인 응답 스키마"""

    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="Access Token 만료 시간 (초)")
    user: OAuthUserInfo = Field(..., description="사용자 정보")
    is_new_user: bool = Field(..., description="신규 가입 여부")


class OAuthUserData(BaseModel):
    """OAuth 제공자로부터 받은 사용자 데이터 (내부 사용)"""

    provider: OAuthProviderEnum
    provider_user_id: str
    email: str
    name: str | None = None
    profile_image: str | None = None
