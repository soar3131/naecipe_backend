"""Contract tests for POST /v1/auth/logout endpoint"""

import pytest
from httpx import AsyncClient


class TestLogoutContract:
    """Contract tests for logout endpoint"""

    @pytest.mark.asyncio
    async def test_logout_success_returns_204(self, client: AsyncClient, valid_user_data: dict):
        """성공적인 로그아웃은 204 No Content를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_logout_no_token_returns_401(self, client: AsyncClient):
        """토큰 없이 로그아웃 요청 시 401 Unauthorized를 반환한다"""
        response = await client.post("/v1/auth/logout")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalid_token_returns_401(self, client: AsyncClient):
        """유효하지 않은 토큰으로 로그아웃 요청 시 401 Unauthorized를 반환한다"""
        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_twice_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """이미 로그아웃한 토큰으로 다시 로그아웃 시 401 Unauthorized를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # First logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Second logout with same token
        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_error_response_rfc7807_format(self, client: AsyncClient):
        """에러 응답은 RFC 7807 Problem Detail 형식을 따른다"""
        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"},
        )

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
