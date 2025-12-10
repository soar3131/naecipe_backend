"""Unit tests for auth service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from user_service.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    InvalidTokenError,
    TokenRevokedError,
)
from user_service.models.user import User, UserStatus
from user_service.services.auth import AuthService


class TestAuthServiceLogin:
    """Tests for AuthService.login()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock dependencies"""
        return AuthService(mock_db)

    @pytest.mark.asyncio
    async def test_login_success_returns_tokens(self, auth_service, mock_db):
        """성공적인 로그인이 토큰을 반환한다"""
        # Setup mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = "user-id-123"
        mock_user.email = "test@example.com"
        mock_user.password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.1Fwv6Q6LXJx9yq"  # "password"
        mock_user.status = UserStatus.ACTIVE
        mock_user.locked_until = None

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        # Mock Redis operations
        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.get_login_failure_count = AsyncMock(return_value=0)
            mock_session.reset_login_failure = AsyncMock()
            mock_session.store_refresh_token = AsyncMock()

            with patch("user_service.services.auth.verify_password", return_value=True):
                response = await auth_service.login("test@example.com", "password")

        assert response.access_token is not None
        assert response.refresh_token is not None
        assert response.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email_raises_error(self, auth_service, mock_db):
        """존재하지 않는 이메일로 로그인 시 AuthenticationError가 발생한다"""
        # Mock no user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.get_login_failure_count = AsyncMock(return_value=0)
            mock_session.increment_login_failure = AsyncMock(return_value=1)

            with pytest.raises(AuthenticationError):
                await auth_service.login("nonexistent@example.com", "password")

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_error(self, auth_service, mock_db):
        """잘못된 비밀번호로 로그인 시 AuthenticationError가 발생한다"""
        mock_user = MagicMock(spec=User)
        mock_user.status = UserStatus.ACTIVE
        mock_user.locked_until = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.get_login_failure_count = AsyncMock(return_value=0)
            mock_session.increment_login_failure = AsyncMock(return_value=1)

            with patch("user_service.services.auth.verify_password", return_value=False):
                with pytest.raises(AuthenticationError):
                    await auth_service.login("test@example.com", "wrong-password")

    @pytest.mark.asyncio
    async def test_login_locked_account_raises_error(self, auth_service, mock_db):
        """잠긴 계정으로 로그인 시 AccountLockedError가 발생한다"""
        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.get_login_failure_count = AsyncMock(return_value=5)

            with pytest.raises(AccountLockedError):
                await auth_service.login("test@example.com", "password")


class TestAuthServiceRefresh:
    """Tests for AuthService.refresh_token()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock dependencies"""
        return AuthService(mock_db)

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_raises_error(self, auth_service):
        """유효하지 않은 Refresh Token으로 갱신 시 InvalidTokenError가 발생한다"""
        with patch("user_service.services.auth.verify_refresh_token", return_value=None):
            with pytest.raises(InvalidTokenError):
                await auth_service.refresh_token("invalid-token")

    @pytest.mark.asyncio
    async def test_refresh_revoked_token_raises_error(self, auth_service, mock_db):
        """취소된 Refresh Token으로 갱신 시 TokenRevokedError가 발생한다"""
        mock_payload = {"sub": "user-id", "type": "refresh"}

        with patch("user_service.services.auth.verify_refresh_token", return_value=mock_payload):
            with patch("user_service.services.auth.SessionService") as mock_session:
                mock_session.get_refresh_token = AsyncMock(return_value=None)

                with pytest.raises(TokenRevokedError):
                    await auth_service.refresh_token("valid-but-revoked-token")


class TestAuthServiceLogout:
    """Tests for AuthService.logout()"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """Create AuthService with mock dependencies"""
        return AuthService(mock_db)

    @pytest.mark.asyncio
    async def test_logout_deletes_session(self, auth_service):
        """로그아웃이 세션을 삭제한다"""
        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.delete_session = AsyncMock()
            mock_session.blacklist_token = AsyncMock()

            await auth_service.logout("user-id", "jti-123", 9999999999)

            mock_session.delete_session.assert_called_once_with("user-id")

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, auth_service):
        """로그아웃이 Access Token을 블랙리스트에 추가한다"""
        with patch("user_service.services.auth.SessionService") as mock_session:
            mock_session.delete_session = AsyncMock()
            mock_session.blacklist_token = AsyncMock()

            await auth_service.logout("user-id", "jti-123", 9999999999)

            mock_session.blacklist_token.assert_called_once()
