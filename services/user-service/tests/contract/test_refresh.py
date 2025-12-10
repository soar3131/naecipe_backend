"""Contract tests for POST /v1/auth/refresh endpoint"""

import pytest
from httpx import AsyncClient


class TestRefreshContract:
    """Contract tests for token refresh endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_success_returns_200(self, client: AsyncClient, valid_user_data: dict):
        """유효한 Refresh Token으로 갱신 시 200 OK를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_success_response_schema(self, client: AsyncClient, valid_user_data: dict):
        """성공 응답은 access_token, refresh_token, token_type, expires_in을 포함한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_returns_401(self, client: AsyncClient):
        """유효하지 않은 Refresh Token은 401 Unauthorized를 반환한다"""
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "invalid_token"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_missing_token_returns_422(self, client: AsyncClient):
        """Refresh Token 누락 시 422를 반환한다"""
        response = await client.post("/v1/auth/refresh", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_revoked_token_returns_401(self, client: AsyncClient, valid_user_data: dict):
        """취소된 Refresh Token은 401 Unauthorized를 반환한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]
        old_refresh_token = login_response.json()["refresh_token"]

        # Logout (revokes tokens)
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Try to refresh with old token
        response = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_error_response_rfc7807_format(self, client: AsyncClient):
        """에러 응답은 RFC 7807 Problem Detail 형식을 따른다"""
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "invalid"})

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
