"""Contract tests for POST /v1/auth/login endpoint"""

import pytest
from httpx import AsyncClient


class TestLoginContract:
    """Contract tests for login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success_returns_200(self, client: AsyncClient, valid_user_data: dict):
        """성공적인 로그인은 200 OK를 반환한다"""
        # Register user first
        await client.post("/v1/auth/register", json=valid_user_data)

        # Login
        response = await client.post("/v1/auth/login", json=valid_user_data)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_success_response_schema(self, client: AsyncClient, valid_user_data: dict):
        """성공 응답은 access_token, refresh_token, token_type, expires_in을 포함한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        response = await client.post("/v1/auth/login", json=valid_user_data)

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """존재하지 않는 이메일로 로그인 시 401 Unauthorized를 반환한다"""
        response = await client.post("/v1/auth/login", json=valid_user_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_password_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """잘못된 비밀번호로 로그인 시 401 Unauthorized를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        wrong_password_data = {**valid_user_data, "password": "WrongPassword123"}
        response = await client.post("/v1/auth/login", json=wrong_password_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_error_response_rfc7807_format(self, client: AsyncClient, valid_user_data: dict):
        """에러 응답은 RFC 7807 Problem Detail 형식을 따른다"""
        response = await client.post("/v1/auth/login", json=valid_user_data)

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_missing_fields_returns_422(self, client: AsyncClient):
        """필수 필드 누락 시 422를 반환한다"""
        response = await client.post("/v1/auth/login", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_locked_account_returns_423(self, client: AsyncClient, valid_user_data: dict):
        """잠긴 계정으로 로그인 시 423 Locked를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        # Fail login 5 times to lock account
        wrong_data = {**valid_user_data, "password": "WrongPassword123"}
        for _ in range(5):
            await client.post("/v1/auth/login", json=wrong_data)

        # 6th attempt should return 423
        response = await client.post("/v1/auth/login", json=valid_user_data)

        assert response.status_code == 423
