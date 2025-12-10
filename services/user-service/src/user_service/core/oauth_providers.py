"""OAuth provider configurations"""

from dataclasses import dataclass
from typing import Any

from user_service.core.config import settings
from user_service.schemas.oauth import OAuthProviderEnum


@dataclass
class OAuthProviderConfig:
    """OAuth provider configuration"""

    provider: OAuthProviderEnum
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_url: str
    token_url: str
    user_info_url: str
    scopes: list[str]


class OAuthProviders:
    """OAuth provider configurations manager"""

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
        """Get provider configuration by provider type"""
        provider_map = {
            OAuthProviderEnum.KAKAO: cls.KAKAO,
            OAuthProviderEnum.GOOGLE: cls.GOOGLE,
            OAuthProviderEnum.NAVER: cls.NAVER,
        }
        return provider_map[provider]

    @classmethod
    def is_supported(cls, provider: str) -> bool:
        """Check if provider is supported"""
        try:
            OAuthProviderEnum(provider)
            return True
        except ValueError:
            return False


def parse_user_info(provider: OAuthProviderEnum, data: dict[str, Any]) -> dict[str, Any]:
    """Parse user info response from OAuth provider

    Each provider returns user info in different format.
    This function normalizes the response.
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
        # Naver wraps response in "response" object
        response = data.get("response", {})
        return {
            "provider_user_id": response.get("id", ""),
            "email": response.get("email", ""),
            "name": response.get("name") or response.get("nickname"),
            "profile_image": response.get("profile_image"),
        }

    return {}
