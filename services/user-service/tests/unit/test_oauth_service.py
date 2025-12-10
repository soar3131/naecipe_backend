"""Unit tests for OAuth service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from user_service.core.exceptions import (
    OAuthAccountAlreadyLinkedError,
    OAuthProviderError,
    OAuthStateError,
)
from user_service.models.oauth_account import OAuthAccount
from user_service.models.user import User, UserStatus
from user_service.schemas.oauth import OAuthProviderEnum, OAuthUserData
from user_service.services.oauth import OAuthService


class TestOAuthServiceGenerateAuthorizationUrl:
    """Tests for OAuthService.generate_authorization_url()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService with mock dependencies"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_generate_kakao_authorization_url(self, oauth_service):
        """카카오 OAuth 인증 URL 생성 테스트"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await oauth_service.generate_authorization_url(
                OAuthProviderEnum.KAKAO
            )

            assert result.authorization_url.startswith("https://kauth.kakao.com/oauth/authorize")
            assert "client_id=" in result.authorization_url
            assert "state=" in result.authorization_url
            assert result.state is not None
            assert len(result.state) > 20  # state는 충분히 긴 랜덤 문자열

            # Redis에 state가 저장되었는지 확인
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_google_authorization_url(self, oauth_service):
        """구글 OAuth 인증 URL 생성 테스트"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await oauth_service.generate_authorization_url(
                OAuthProviderEnum.GOOGLE
            )

            assert result.authorization_url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
            assert "scope=" in result.authorization_url
            assert result.state is not None

    @pytest.mark.asyncio
    async def test_generate_naver_authorization_url(self, oauth_service):
        """네이버 OAuth 인증 URL 생성 테스트"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis

            result = await oauth_service.generate_authorization_url(
                OAuthProviderEnum.NAVER
            )

            assert result.authorization_url.startswith("https://nid.naver.com/oauth2.0/authorize")
            assert result.state is not None


class TestOAuthServiceValidateState:
    """Tests for OAuthService._validate_state()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService with mock dependencies"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_validate_state_success(self, oauth_service):
        """유효한 state 검증 성공 테스트"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = "kakao"
            mock_get_redis.return_value = mock_redis

            # Should not raise
            await oauth_service._validate_state("valid-state", OAuthProviderEnum.KAKAO)

            # State should be deleted after use
            mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_state_not_found_raises_error(self, oauth_service):
        """존재하지 않는 state로 검증 시 OAuthStateError 발생"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_get_redis.return_value = mock_redis

            with pytest.raises(OAuthStateError):
                await oauth_service._validate_state("invalid-state", OAuthProviderEnum.KAKAO)

    @pytest.mark.asyncio
    async def test_validate_state_provider_mismatch_raises_error(self, oauth_service):
        """provider가 일치하지 않을 때 OAuthStateError 발생"""
        with patch("user_service.services.oauth.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = "google"  # 저장된 provider는 google
            mock_get_redis.return_value = mock_redis

            with pytest.raises(OAuthStateError):
                # kakao로 검증 시도
                await oauth_service._validate_state("valid-state", OAuthProviderEnum.KAKAO)


class TestOAuthServiceExchangeCodeForToken:
    """Tests for OAuthService._exchange_code_for_token()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService with mock dependencies"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_exchange_code_success(self, oauth_service):
        """인증 코드 교환 성공 테스트"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test-access-token"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            token = await oauth_service._exchange_code_for_token(
                OAuthProviderEnum.KAKAO, "auth-code"
            )

            assert token == "test-access-token"

    @pytest.mark.asyncio
    async def test_exchange_code_no_token_raises_error(self, oauth_service):
        """액세스 토큰이 없을 때 OAuthProviderError 발생"""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No access_token
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(OAuthProviderError):
                await oauth_service._exchange_code_for_token(
                    OAuthProviderEnum.KAKAO, "auth-code"
                )


class TestOAuthServiceFindOrCreateUser:
    """Tests for OAuthService._find_or_create_user()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService with mock dependencies"""
        return OAuthService(mock_db)

    @pytest.fixture
    def oauth_user_data(self):
        """Create sample OAuth user data"""
        return OAuthUserData(
            provider=OAuthProviderEnum.KAKAO,
            provider_user_id="kakao-12345",
            email="user@example.com",
            name="Test User",
            profile_image="https://example.com/image.jpg",
        )

    @pytest.mark.asyncio
    async def test_find_existing_oauth_account(self, oauth_service, mock_db, oauth_user_data):
        """기존 OAuth 계정이 있으면 해당 사용자 반환"""
        mock_user = MagicMock(spec=User)
        mock_user.id = "user-id-123"

        mock_oauth_account = MagicMock(spec=OAuthAccount)
        mock_oauth_account.user_id = "user-id-123"

        # Mock OAuth account lookup
        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = mock_oauth_account

        # Mock user lookup
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = mock_user

        mock_db.execute.side_effect = [mock_result_oauth, mock_result_user]

        user, oauth_account, is_new_user = await oauth_service._find_or_create_user(
            oauth_user_data
        )

        assert user == mock_user
        assert oauth_account == mock_oauth_account
        assert is_new_user is False

    @pytest.mark.asyncio
    async def test_link_to_existing_user_by_email(self, oauth_service, mock_db, oauth_user_data):
        """동일 이메일 사용자가 있으면 OAuth 계정 연결"""
        mock_user = MagicMock(spec=User)
        mock_user.id = "existing-user-id"

        # OAuth account not found
        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = None

        # User found by email
        mock_result_email = MagicMock()
        mock_result_email.scalar_one_or_none.return_value = mock_user

        mock_db.execute.side_effect = [mock_result_oauth, mock_result_email]

        user, oauth_account, is_new_user = await oauth_service._find_or_create_user(
            oauth_user_data
        )

        assert user == mock_user
        assert is_new_user is False
        # New OAuth account should be added
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_create_new_user(self, oauth_service, mock_db, oauth_user_data):
        """신규 사용자 생성 테스트"""
        # OAuth account not found
        mock_result_oauth = MagicMock()
        mock_result_oauth.scalar_one_or_none.return_value = None

        # User not found by email
        mock_result_email = MagicMock()
        mock_result_email.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result_oauth, mock_result_email]

        user, oauth_account, is_new_user = await oauth_service._find_or_create_user(
            oauth_user_data
        )

        assert is_new_user is True
        # Both user and oauth account should be added
        assert mock_db.add.call_count == 2


class TestOAuthServiceLinkAccount:
    """Tests for OAuthService.link_account()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def oauth_service(self, mock_db):
        """Create OAuthService with mock dependencies"""
        return OAuthService(mock_db)

    @pytest.mark.asyncio
    async def test_link_already_linked_raises_error(self, oauth_service, mock_db):
        """이미 연결된 OAuth 계정 연동 시 OAuthAccountAlreadyLinkedError 발생"""
        existing_oauth = MagicMock(spec=OAuthAccount)

        # Mock state validation
        with patch.object(oauth_service, "_validate_state", new=AsyncMock()):
            # Mock token exchange
            with patch.object(
                oauth_service, "_exchange_code_for_token", new=AsyncMock(return_value="token")
            ):
                # Mock user info
                with patch.object(
                    oauth_service,
                    "_get_user_info",
                    new=AsyncMock(
                        return_value=OAuthUserData(
                            provider=OAuthProviderEnum.KAKAO,
                            provider_user_id="kakao-12345",
                            email="user@example.com",
                        )
                    ),
                ):
                    # Mock existing OAuth account
                    mock_result = MagicMock()
                    mock_result.scalar_one_or_none.return_value = existing_oauth
                    mock_db.execute.return_value = mock_result

                    with pytest.raises(OAuthAccountAlreadyLinkedError):
                        await oauth_service.link_account(
                            user_id="user-id",
                            provider=OAuthProviderEnum.KAKAO,
                            code="auth-code",
                            state="valid-state",
                        )


class TestParseUserInfo:
    """Tests for parse_user_info()"""

    def test_parse_kakao_user_info(self):
        """카카오 사용자 정보 파싱 테스트"""
        from user_service.core.oauth_providers import parse_user_info

        kakao_data = {
            "id": 12345,
            "kakao_account": {
                "email": "user@kakao.com",
                "profile": {
                    "nickname": "카카오유저",
                    "profile_image_url": "https://k.kakaocdn.net/image.jpg",
                },
            },
        }

        result = parse_user_info(OAuthProviderEnum.KAKAO, kakao_data)

        assert result["provider_user_id"] == "12345"
        assert result["email"] == "user@kakao.com"
        assert result["name"] == "카카오유저"
        assert result["profile_image"] == "https://k.kakaocdn.net/image.jpg"

    def test_parse_google_user_info(self):
        """구글 사용자 정보 파싱 테스트"""
        from user_service.core.oauth_providers import parse_user_info

        google_data = {
            "id": "google-user-id",
            "email": "user@gmail.com",
            "name": "Google User",
            "picture": "https://lh3.googleusercontent.com/image.jpg",
        }

        result = parse_user_info(OAuthProviderEnum.GOOGLE, google_data)

        assert result["provider_user_id"] == "google-user-id"
        assert result["email"] == "user@gmail.com"
        assert result["name"] == "Google User"
        assert result["profile_image"] == "https://lh3.googleusercontent.com/image.jpg"

    def test_parse_naver_user_info(self):
        """네이버 사용자 정보 파싱 테스트"""
        from user_service.core.oauth_providers import parse_user_info

        naver_data = {
            "response": {
                "id": "naver-user-id",
                "email": "user@naver.com",
                "name": "네이버유저",
                "profile_image": "https://phinf.naver.net/image.jpg",
            }
        }

        result = parse_user_info(OAuthProviderEnum.NAVER, naver_data)

        assert result["provider_user_id"] == "naver-user-id"
        assert result["email"] == "user@naver.com"
        assert result["name"] == "네이버유저"
        assert result["profile_image"] == "https://phinf.naver.net/image.jpg"
