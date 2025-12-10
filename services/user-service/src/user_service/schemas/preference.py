"""
취향 설정 관련 Pydantic 스키마
SPEC-003: 사용자 프로필 및 취향 설정
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import Allergy, CuisineCategory, DietaryRestriction


class TasteValues(BaseModel):
    """맛 취향 값 (1-5 스케일)"""
    sweetness: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="단맛 선호도 (1-5)"
    )
    saltiness: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="짠맛 선호도 (1-5)"
    )
    spiciness: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="매운맛 선호도 (1-5)"
    )
    sourness: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="신맛 선호도 (1-5)"
    )


class PreferencesUpdateRequest(BaseModel):
    """취향 설정 수정 요청 스키마"""
    dietary_restrictions: Optional[List[DietaryRestriction]] = Field(
        None,
        description="식이 제한 목록",
        alias="dietaryRestrictions"
    )
    allergies: Optional[List[Allergy]] = Field(
        None,
        description="알레르기 목록"
    )
    cuisine_preferences: Optional[List[CuisineCategory]] = Field(
        None,
        max_length=10,
        description="선호 요리 카테고리 목록 (최대 10개)",
        alias="cuisinePreferences"
    )
    skill_level: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="요리 실력 수준 (1-5)",
        alias="skillLevel"
    )
    household_size: Optional[int] = Field(
        None,
        ge=1,
        le=20,
        description="가구 인원 수 (1-20)",
        alias="householdSize"
    )
    taste_preferences: Optional[Dict[str, TasteValues]] = Field(
        None,
        description="맛 취향 (overall 또는 카테고리별)",
        alias="tastePreferences"
    )

    @field_validator("cuisine_preferences")
    @classmethod
    def validate_cuisine_preferences_count(cls, v: Optional[List[CuisineCategory]]) -> Optional[List[CuisineCategory]]:
        """선호 요리 카테고리 최대 10개 제한"""
        if v is not None and len(v) > 10:
            raise ValueError("선호 요리 카테고리는 최대 10개까지 설정 가능합니다")
        return v

    @field_validator("taste_preferences")
    @classmethod
    def validate_taste_preference_keys(cls, v: Optional[Dict[str, TasteValues]]) -> Optional[Dict[str, TasteValues]]:
        """맛 취향 키 검증 (overall 또는 CuisineCategory만 허용)"""
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
        default_factory=list,
        description="식이 제한 목록",
        alias="dietaryRestrictions"
    )
    allergies: List[str] = Field(
        default_factory=list,
        description="알레르기 목록"
    )
    cuisine_preferences: List[str] = Field(
        default_factory=list,
        description="선호 요리 카테고리 목록",
        alias="cuisinePreferences"
    )
    skill_level: Optional[int] = Field(
        None,
        description="요리 실력 수준 (1-5)",
        alias="skillLevel"
    )
    household_size: Optional[int] = Field(
        None,
        description="가구 인원 수 (1-20)",
        alias="householdSize"
    )
    taste_preferences: Dict[str, TastePreferenceData] = Field(
        default_factory=dict,
        description="맛 취향",
        alias="tastePreferences"
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="취향 설정 수정 시각",
        alias="updatedAt"
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
