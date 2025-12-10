"""Contract tests for OAuth endpoints"""

import pytest
from httpx import AsyncClient


class TestOAuthAuthorizationUrlContract:
    """Contract tests for GET /v1/auth/oauth/{provider} endpoint"""

    @pytest.mark.asyncio
    async def test_kakao_auth_url_returns_200(self, client: AsyncClient):
        """카카오 인증 URL 요청은 200 OK를 반환한다"""
        response = await client.get("/v1/auth/oauth/kakao")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_google_auth_url_returns_200(self, client: AsyncClient):
        """구글 인증 URL 요청은 200 OK를 반환한다"""
        response = await client.get("/v1/auth/oauth/google")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_naver_auth_url_returns_200(self, client: AsyncClient):
        """네이버 인증 URL 요청은 200 OK를 반환한다"""
        response = await client.get("/v1/auth/oauth/naver")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_url_response_schema(self, client: AsyncClient):
        """인증 URL 응답은 authorization_url과 state를 포함한다"""
        response = await client.get("/v1/auth/oauth/kakao")

        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert len(data["state"]) > 20  # state는 충분히 긴 랜덤 문자열

    @pytest.mark.asyncio
    async def test_unsupported_provider_returns_400(self, client: AsyncClient):
        """지원하지 않는 provider 요청은 400을 반환한다"""
        response = await client.get("/v1/auth/oauth/unsupported")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unsupported_provider_error_rfc7807_format(self, client: AsyncClient):
        """지원하지 않는 provider 에러 응답은 RFC 7807 형식을 따른다"""
        response = await client.get("/v1/auth/oauth/unsupported")

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert data["status"] == 400


class TestOAuthCallbackContract:
    """Contract tests for POST /v1/auth/oauth/{provider}/callback endpoint"""

    @pytest.mark.asyncio
    async def test_callback_missing_fields_returns_422(self, client: AsyncClient):
        """필수 필드 누락 시 422를 반환한다"""
        response = await client.post("/v1/auth/oauth/kakao/callback", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_400(self, client: AsyncClient):
        """유효하지 않은 state로 콜백 시 400을 반환한다"""
        response = await client.post(
            "/v1/auth/oauth/kakao/callback",
            json={"code": "test-code", "state": "invalid-state"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_callback_invalid_state_error_rfc7807_format(self, client: AsyncClient):
        """유효하지 않은 state 에러 응답은 RFC 7807 형식을 따른다"""
        response = await client.post(
            "/v1/auth/oauth/kakao/callback",
            json={"code": "test-code", "state": "invalid-state"},
        )

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_unsupported_provider_callback_returns_400(self, client: AsyncClient):
        """지원하지 않는 provider 콜백 요청은 400을 반환한다"""
        response = await client.post(
            "/v1/auth/oauth/unsupported/callback",
            json={"code": "test-code", "state": "test-state"},
        )

        assert response.status_code == 400


class TestOAuthLinkContract:
    """Contract tests for POST /v1/auth/oauth/{provider}/link endpoint"""

    @pytest.mark.asyncio
    async def test_link_without_auth_returns_401(self, client: AsyncClient):
        """인증 없이 계정 연동 요청 시 401을 반환한다"""
        response = await client.post(
            "/v1/auth/oauth/kakao/link",
            json={"code": "test-code", "state": "test-state"},
        )

        # 403 or 401 depending on FastAPI version/configuration
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_link_missing_fields_returns_422(self, client: AsyncClient, valid_user_data: dict):
        """필수 필드 누락 시 422를 반환한다"""
        # Register and login to get token
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        token = login_response.json()["access_token"]

        response = await client.post(
            "/v1/auth/oauth/kakao/link",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unsupported_provider_link_returns_400(self, client: AsyncClient, valid_user_data: dict):
        """지원하지 않는 provider 연동 요청은 400을 반환한다"""
        # Register and login to get token
        await client.post("/v1/auth/register", json=valid_user_data)
        login_response = await client.post("/v1/auth/login", json=valid_user_data)
        token = login_response.json()["access_token"]

        response = await client.post(
            "/v1/auth/oauth/unsupported/link",
            json={"code": "test-code", "state": "test-state"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
