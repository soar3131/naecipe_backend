"""Unit tests for security utilities"""

import time

import pytest

from user_service.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_access_token,
    verify_password,
    verify_refresh_token,
)


class TestPasswordHashing:
    """Tests for password hashing utilities"""

    def test_hash_password_returns_bcrypt_hash(self):
        """비밀번호 해시가 bcrypt 형식이다"""
        password = "TestPassword123"
        hashed = hash_password(password)

        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_hash_password_different_each_time(self):
        """같은 비밀번호도 매번 다른 해시를 생성한다"""
        password = "TestPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """올바른 비밀번호 검증이 True를 반환한다"""
        password = "TestPassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_wrong_password(self):
        """잘못된 비밀번호 검증이 False를 반환한다"""
        password = "TestPassword123"
        hashed = hash_password(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_verify_password_empty_password(self):
        """빈 비밀번호 검증이 False를 반환한다"""
        password = "TestPassword123"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token utilities"""

    def test_create_access_token_returns_string(self):
        """Access Token 생성이 문자열을 반환한다"""
        user_id = "test-user-id"
        token = create_access_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_returns_string(self):
        """Refresh Token 생성이 문자열을 반환한다"""
        user_id = "test-user-id"
        token = create_refresh_token(user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_user_id(self):
        """Access Token에 사용자 ID가 포함되어 있다"""
        user_id = "test-user-id-123"
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id

    def test_access_token_has_correct_type(self):
        """Access Token의 type이 'access'이다"""
        token = create_access_token("user-id")
        payload = decode_token(token)

        assert payload is not None
        assert payload["type"] == "access"

    def test_refresh_token_has_correct_type(self):
        """Refresh Token의 type이 'refresh'이다"""
        token = create_refresh_token("user-id")
        payload = decode_token(token)

        assert payload is not None
        assert payload["type"] == "refresh"

    def test_access_token_has_jti(self):
        """Access Token에 jti가 포함되어 있다"""
        token = create_access_token("user-id")
        payload = decode_token(token)

        assert payload is not None
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_access_token_has_expiry(self):
        """Access Token에 만료 시간이 포함되어 있다"""
        token = create_access_token("user-id")
        payload = decode_token(token)

        assert payload is not None
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_verify_access_token_valid(self):
        """유효한 Access Token 검증이 성공한다"""
        token = create_access_token("user-id")
        payload = verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == "user-id"

    def test_verify_access_token_with_refresh_token(self):
        """Refresh Token을 Access Token으로 검증하면 실패한다"""
        token = create_refresh_token("user-id")
        payload = verify_access_token(token)

        assert payload is None

    def test_verify_refresh_token_valid(self):
        """유효한 Refresh Token 검증이 성공한다"""
        token = create_refresh_token("user-id")
        payload = verify_refresh_token(token)

        assert payload is not None
        assert payload["sub"] == "user-id"

    def test_verify_refresh_token_with_access_token(self):
        """Access Token을 Refresh Token으로 검증하면 실패한다"""
        token = create_access_token("user-id")
        payload = verify_refresh_token(token)

        assert payload is None

    def test_decode_invalid_token(self):
        """유효하지 않은 토큰 디코딩이 None을 반환한다"""
        payload = decode_token("invalid.token.here")

        assert payload is None

    def test_decode_empty_token(self):
        """빈 토큰 디코딩이 None을 반환한다"""
        payload = decode_token("")

        assert payload is None

    def test_different_users_get_different_tokens(self):
        """다른 사용자는 다른 토큰을 받는다"""
        token1 = create_access_token("user-1")
        token2 = create_access_token("user-2")

        assert token1 != token2

    def test_same_user_gets_different_tokens(self):
        """같은 사용자도 매번 다른 토큰을 받는다 (jti가 다름)"""
        token1 = create_access_token("user-id")
        token2 = create_access_token("user-id")

        assert token1 != token2

        payload1 = decode_token(token1)
        payload2 = decode_token(token2)

        assert payload1["jti"] != payload2["jti"]
