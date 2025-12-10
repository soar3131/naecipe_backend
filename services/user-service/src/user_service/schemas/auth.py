"""Authentication Pydantic schemas"""

import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from user_service.core.config import settings


class RegisterRequest(BaseModel):
    """Request schema for user registration"""

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
        """Validate password meets policy requirements"""
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"비밀번호는 최소 {settings.PASSWORD_MIN_LENGTH}자 이상이어야 합니다.")

        # Check for at least one letter
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("비밀번호는 최소 1개의 영문자를 포함해야 합니다.")

        # Check for at least one number
        if not re.search(r"\d", v):
            raise ValueError("비밀번호는 최소 1개의 숫자를 포함해야 합니다.")

        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower().strip()


class LoginRequest(BaseModel):
    """Request schema for user login"""

    email: EmailStr = Field(..., description="사용자 이메일 주소")
    password: str = Field(..., description="비밀번호")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase"""
        return v.lower().strip()


class TokenResponse(BaseModel):
    """Response schema for token issuance"""

    access_token: str = Field(..., description="JWT Access Token (유효기간 15분)")
    refresh_token: str = Field(..., description="JWT Refresh Token (유효기간 7일)")
    token_type: Literal["bearer"] = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="Access Token 만료까지 남은 시간 (초)")


class RefreshRequest(BaseModel):
    """Request schema for token refresh"""

    refresh_token: str = Field(..., description="Refresh Token")
