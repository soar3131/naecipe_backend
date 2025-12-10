"""
프로필 관련 Pydantic 스키마
SPEC-003: 사용자 프로필 및 취향 설정
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ProfileUpdateRequest(BaseModel):
    """프로필 수정 요청 스키마"""
    display_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="표시 이름 (1-50자)",
        alias="displayName",
        examples=["홍길동"]
    )
    profile_image_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="프로필 이미지 URL",
        alias="profileImageUrl",
        examples=["https://cdn.naecipe.com/profiles/user123.jpg"]
    )

    @field_validator("profile_image_url")
    @classmethod
    def validate_url_format(cls, v: Optional[str]) -> Optional[str]:
        """URL 형식 검증 (http/https만 허용)"""
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
    display_name: str = Field(
        ...,
        description="표시 이름",
        alias="displayName"
    )
    profile_image_url: Optional[str] = Field(
        None,
        description="프로필 이미지 URL",
        alias="profileImageUrl"
    )
    created_at: datetime = Field(..., description="계정 생성 시각", alias="createdAt")
    updated_at: datetime = Field(..., description="프로필 수정 시각", alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class ProfileResponse(BaseModel):
    """프로필 API 응답"""
    success: bool = True
    data: ProfileData
