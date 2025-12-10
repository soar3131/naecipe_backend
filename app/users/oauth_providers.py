"""
OAuth 제공자 설정

카카오, 구글, 네이버 OAuth 설정을 관리합니다.
"""

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.users.schemas import OAuthProviderEnum


@dataclass
class OAuthProviderConfig:
    """OAuth 제공자 설정"""

    provider: OAuthProviderEnum
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_url: str
    token_url: str
    user_info_url: str
    scopes: list[str]


class OAuthProviders:
    """OAuth 제공자 설정 관리자"""

    KAKAO = OAuthProviderConfig(
        provider=OAuthProviderEnum.KAKAO,
        client_id=settings.KAKAO_CLIENT_ID,
        client_secret=settings.KAKAO_CLIENT_SECRET,
        redirect_uri=settings.KAKAO_REDIRECT_URI,
        authorization_url="https://kauth.kakao.com/oauth/authorize",
        token_url="https://kauth.kakao.com/oauth/token",
        user_info_url="https://kapi.kakao.com/v2/user/me",
        scopes=["profile_nickname", "account_email"],
    )

    GOOGLE = OAuthProviderConfig(
        provider=OAuthProviderEnum.GOOGLE,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        user_info_url="https://www.googleapis.com/oauth2/v2/userinfo",
        scopes=["openid", "email", "profile"],
    )

    NAVER = OAuthProviderConfig(
        provider=OAuthProviderEnum.NAVER,
        client_id=settings.NAVER_CLIENT_ID,
        client_secret=settings.NAVER_CLIENT_SECRET,
        redirect_uri=settings.NAVER_REDIRECT_URI,
        authorization_url="https://nid.naver.com/oauth2.0/authorize",
        token_url="https://nid.naver.com/oauth2.0/token",
        user_info_url="https://openapi.naver.com/v1/nid/me",
        scopes=[],
    )

    @classmethod
    def get(cls, provider: OAuthProviderEnum) -> OAuthProviderConfig:
        """제공자 설정 조회"""
        provider_map = {
            OAuthProviderEnum.KAKAO: cls.KAKAO,
            OAuthProviderEnum.GOOGLE: cls.GOOGLE,
            OAuthProviderEnum.NAVER: cls.NAVER,
        }
        return provider_map[provider]

    @classmethod
    def is_supported(cls, provider: str) -> bool:
        """지원 제공자 여부 확인"""
        try:
            OAuthProviderEnum(provider)
            return True
        except ValueError:
            return False


def parse_user_info(provider: OAuthProviderEnum, data: dict[str, Any]) -> dict[str, Any]:
    """OAuth 제공자의 사용자 정보 응답 파싱

    각 제공자마다 다른 형식으로 반환하는 사용자 정보를 통일된 형태로 변환합니다.
    """
    if provider == OAuthProviderEnum.KAKAO:
        kakao_account = data.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        return {
            "provider_user_id": str(data.get("id", "")),
            "email": kakao_account.get("email", ""),
            "name": profile.get("nickname"),
            "profile_image": profile.get("profile_image_url"),
        }

    elif provider == OAuthProviderEnum.GOOGLE:
        return {
            "provider_user_id": data.get("id", ""),
            "email": data.get("email", ""),
            "name": data.get("name"),
            "profile_image": data.get("picture"),
        }

    elif provider == OAuthProviderEnum.NAVER:
        response = data.get("response", {})
        return {
            "provider_user_id": response.get("id", ""),
            "email": response.get("email", ""),
            "name": response.get("name") or response.get("nickname"),
            "profile_image": response.get("profile_image"),
        }

    return {}
