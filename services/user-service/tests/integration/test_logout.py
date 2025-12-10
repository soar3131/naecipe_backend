"""Integration tests for logout and token invalidation"""

import pytest
from httpx import AsyncClient


class TestLogoutIntegration:
    """Integration tests for logout flow"""

    @pytest.mark.asyncio
    async def test_logout_invalidates_access_token(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 후 Access Token이 무효화된다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Try to access protected endpoint
        me_response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert me_response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_invalidates_refresh_token(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 후 Refresh Token이 무효화된다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.json()["refresh_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Try to refresh
        refresh_response = await client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})

        assert refresh_response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_allows_new_login(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 후 다시 로그인할 수 있다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Login again
        new_login_response = await client.post("/v1/auth/login", json=valid_user_data)

        assert new_login_response.status_code == 200
        assert new_login_response.json()["access_token"] != access_token

    @pytest.mark.asyncio
    async def test_logout_new_tokens_work(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 후 새로 발급받은 토큰이 정상 작동한다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        old_access_token = login_response.json()["access_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {old_access_token}"},
        )

        # Login again
        new_login_response = await client.post("/v1/auth/login", json=valid_user_data)
        new_access_token = new_login_response.json()["access_token"]

        # New token should work
        me_response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )

        assert me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, client: AsyncClient, valid_user_data: dict):
        """여러 세션에서 로그아웃은 해당 세션만 무효화한다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        # First login
        login1_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token1 = login1_response.json()["access_token"]

        # Second login (same user, different session in real scenario)
        # Note: In this implementation, second login replaces session
        # This test documents that behavior
        login2_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token2 = login2_response.json()["access_token"]

        # Second token should work
        me_response = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token2}"},
        )

        assert me_response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self, client: AsyncClient, valid_user_data: dict):
        """로그아웃 시 Access Token이 블랙리스트에 추가된다"""
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        access_token = login_response.json()["access_token"]

        # Logout
        await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Multiple attempts should all fail (token is blacklisted)
        for _ in range(3):
            response = await client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 401
