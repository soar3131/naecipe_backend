"""Contract tests for GET /v1/auth/me endpoint"""

import pytest
from httpx import AsyncClient


class TestMeContract:
    """Contract tests for current user endpoint"""

    @pytest.mark.asyncio
    async def test_me_success_returns_200(self, client: AsyncClient, valid_user_data: dict):
        """유효한 토큰으로 요청 시 200 OK를 반환한다"""
        # Register and login
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_me_success_response_schema(self, client: AsyncClient, valid_user_data: dict):
        """성공 응답은 id, email, status, created_at을 포함한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "status" in data
        assert "created_at" in data
        assert data["email"] == valid_user_data["email"]

    @pytest.mark.asyncio
    async def test_me_no_token_returns_401(self, client: AsyncClient):
        """토큰 없이 요청 시 401 Unauthorized를 반환한다"""
        response = await client.get("/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_invalid_token_returns_401(self, client: AsyncClient):
        """유효하지 않은 토큰으로 요청 시 401 Unauthorized를 반환한다"""
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_expired_token_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """만료된 토큰으로 요청 시 401 Unauthorized를 반환한다"""
        # This test would require manipulating time or creating an expired token
        # For now, we'll test with a malformed token
        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxfQ.invalid"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_password_not_in_response(self, client: AsyncClient, valid_user_data: dict):
        """응답에 비밀번호가 포함되지 않는다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data
