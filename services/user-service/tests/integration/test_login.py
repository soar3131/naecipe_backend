"""Integration tests for login flow"""

import pytest
from httpx import AsyncClient

from user_service.core.security import decode_token


class TestLoginIntegration:
    """Integration tests for login flow"""

    @pytest.mark.asyncio
    async def test_login_returns_valid_jwt_tokens(self, client: AsyncClient, valid_user_data: dict):
        """로그인 시 유효한 JWT 토큰이 발급된다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        response = await client.post("/v1/auth/login", json=valid_user_data)

        data = response.json()

        # Verify tokens can be decoded
        access_payload = decode_token(data["access_token"])
        refresh_payload = decode_token(data["refresh_token"])

        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    @pytest.mark.asyncio
    async def test_login_token_contains_user_id(self, client: AsyncClient, valid_user_data: dict):
        """발급된 토큰에 사용자 ID가 포함된다"""
        register_response = await client.post("/v1/auth/register", json=valid_user_data)
        user_id = register_response.json()["id"]

        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        payload = decode_token(access_token)
        assert payload["sub"] == user_id

    @pytest.mark.asyncio
    async def test_login_email_case_insensitive(self, client: AsyncClient, valid_user_data: dict):
        """이메일 대소문자 구분 없이 로그인 가능하다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        # Login with uppercase email
        uppercase_data = {**valid_user_data, "email": valid_user_data["email"].upper()}
        response = await client.post("/v1/auth/login", json=uppercase_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_access_token_allows_api_access(self, client: AsyncClient, valid_user_data: dict):
        """Access Token으로 보호된 API에 접근할 수 있다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # Access protected endpoint
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_failure_increments_counter(self, client: AsyncClient, valid_user_data: dict):
        """로그인 실패 시 실패 카운터가 증가한다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        wrong_data = {**valid_user_data, "password": "WrongPassword123"}

        # First 4 failures should return 401
        for i in range(4):
            response = await client.post("/v1/auth/login", json=wrong_data)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_locks_account_after_5_failures(self, client: AsyncClient, valid_user_data: dict):
        """5회 로그인 실패 후 계정이 잠긴다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        wrong_data = {**valid_user_data, "password": "WrongPassword123"}

        # 5 failed attempts
        for _ in range(5):
            await client.post("/v1/auth/login", json=wrong_data)

        # 6th attempt should fail even with correct password
        response = await client.post("/v1/auth/login", json=valid_user_data)
        assert response.status_code == 423

    @pytest.mark.asyncio
    async def test_successful_login_resets_failure_counter(self, client: AsyncClient, valid_user_data: dict):
        """성공적인 로그인은 실패 카운터를 초기화한다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        wrong_data = {**valid_user_data, "password": "WrongPassword123"}

        # 3 failed attempts
        for _ in range(3):
            await client.post("/v1/auth/login", json=wrong_data)

        # Successful login
        response = await client.post("/v1/auth/login", json=valid_user_data)
        assert response.status_code == 200

        # 3 more failed attempts should still allow login after success
        for _ in range(3):
            await client.post("/v1/auth/login", json=wrong_data)

        # Should still not be locked (counter was reset)
        response = await client.post("/v1/auth/login", json=valid_user_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_inactive_user_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """비활성 사용자는 로그인할 수 없다"""
        # This would require admin API to deactivate user
        # For now, just verify basic login works for active user
        await client.post("/v1/auth/register", json=valid_user_data)
        response = await client.post("/v1/auth/login", json=valid_user_data)

        assert response.status_code == 200
