"""Integration tests for token refresh flow"""

import pytest
from httpx import AsyncClient

from user_service.core.security import decode_token


class TestRefreshIntegration:
    """Integration tests for token refresh flow"""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_tokens(self, client: AsyncClient, valid_user_data: dict):
        """토큰 갱신 시 새로운 토큰들이 발급된다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        old_access_token = login_response.json()["access_token"]
        old_refresh_token = login_response.json()["refresh_token"]

        response = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})

        data = response.json()
        assert data["access_token"] != old_access_token
        assert data["refresh_token"] != old_refresh_token

    @pytest.mark.asyncio
    async def test_refresh_new_tokens_are_valid(self, client: AsyncClient, valid_user_data: dict):
        """새로 발급된 토큰들이 유효하다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        refresh_token = login_response.json()["refresh_token"]

        refresh_response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        new_access_token = refresh_response.json()["access_token"]

        # New access token should work
        me_response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )

        assert me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_rotates_refresh_token(self, client: AsyncClient, valid_user_data: dict):
        """토큰 갱신 시 Refresh Token이 교체된다 (rotation)"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        old_refresh_token = login_response.json()["refresh_token"]

        # First refresh
        refresh_response = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})
        new_refresh_token = refresh_response.json()["refresh_token"]

        # Old refresh token should no longer work
        second_refresh = await client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})
        assert second_refresh.status_code == 401

        # New refresh token should work
        third_refresh = await client.post("/v1/auth/refresh", json={"refresh_token": new_refresh_token})
        assert third_refresh.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_preserves_user_identity(self, client: AsyncClient, valid_user_data: dict):
        """갱신된 토큰은 동일한 사용자를 나타낸다"""
        register_response = await client.post("/v1/auth/register", json=valid_user_data)
        user_id = register_response.json()["id"]

        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        refresh_token = login_response.json()["refresh_token"]

        refresh_response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        new_access_token = refresh_response.json()["access_token"]

        # Verify same user ID in new token
        payload = decode_token(new_access_token)
        assert payload["sub"] == user_id

    @pytest.mark.asyncio
    async def test_refresh_chain_works(self, client: AsyncClient, valid_user_data: dict):
        """여러 번 연속으로 토큰 갱신이 가능하다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        refresh_token = login_response.json()["refresh_token"]

        # Chain of refreshes
        for _ in range(3):
            response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
            assert response.status_code == 200
            refresh_token = response.json()["refresh_token"]

    @pytest.mark.asyncio
    async def test_refresh_fails_after_logout(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 후에는 Refresh Token을 사용할 수 없다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Refresh should fail
        response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 401
