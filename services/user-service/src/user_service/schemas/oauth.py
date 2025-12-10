"""OAuth Pydantic schemas"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OAuthProviderEnum(str, Enum):
    """OAuth provider types for API"""

    KAKAO = "kakao"
    GOOGLE = "google"
    NAVER = "naver"


# Request Schemas


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request schema"""

    code: str = Field(..., description="OAuth authorization code")
    state: str = Field(..., description="CSRF 방지용 state 토큰")


# Response Schemas


class OAuthAuthorizationResponse(BaseModel):
    """OAuth authorization URL response schema"""

    authorization_url: str = Field(..., description="소셜 로그인 페이지 URL")
    state: str = Field(..., description="CSRF 방지용 state 토큰")


class OAuthUserInfo(BaseModel):
    """OAuth user info response schema"""

    id: str = Field(..., description="사용자 ID")
    email: str = Field(..., description="이메일 주소")
    provider: OAuthProviderEnum = Field(..., description="OAuth 제공자")
    created_at: datetime | None = Field(None, description="계정 생성 시각")


class OAuthLoginResponse(BaseModel):
    """OAuth login response schema"""

    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="Access Token 만료 시간 (초)")
    user: OAuthUserInfo = Field(..., description="사용자 정보")
    is_new_user: bool = Field(..., description="신규 가입 여부")


# Internal Schemas (for service layer)


class OAuthUserData(BaseModel):
    """OAuth user data from provider"""

    provider: OAuthProviderEnum
    provider_user_id: str
    email: str
    name: str | None = None
    profile_image: str | None = None
