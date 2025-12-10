"""Contract tests for POST /v1/auth/register endpoint"""

import pytest
from httpx import AsyncClient


class TestRegisterContract:
    """Contract tests for registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_success_returns_201(self, client: AsyncClient, valid_user_data: dict):
        """성공적인 회원가입은 201 Created를 반환한다"""
        response = await client.post("/v1/auth/register", json=valid_user_data)

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_register_success_response_schema(self, client: AsyncClient, valid_user_data: dict):
        """성공 응답은 id, email, created_at 필드를 포함한다"""
        response = await client.post("/v1/auth/register", json=valid_user_data)

        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "created_at" in data
        assert data["email"] == valid_user_data["email"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, client: AsyncClient, valid_user_data: dict):
        """중복 이메일로 가입 시 409 Conflict를 반환한다"""
        # First registration
        await client.post("/v1/auth/register", json=valid_user_data)

        # Duplicate registration
        response = await client.post("/v1/auth/register", json=valid_user_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email_returns_422(self, client: AsyncClient, invalid_email_data: dict):
        """유효하지 않은 이메일 형식은 422 Unprocessable Entity를 반환한다"""
        response = await client.post("/v1/auth/register", json=invalid_email_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password_returns_422(self, client: AsyncClient, invalid_password_data: dict):
        """비밀번호 정책 미충족 시 422 Unprocessable Entity를 반환한다"""
        response = await client.post("/v1/auth/register", json=invalid_password_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_error_response_rfc7807_format(self, client: AsyncClient, invalid_email_data: dict):
        """에러 응답은 RFC 7807 Problem Detail 형식을 따른다"""
        response = await client.post("/v1/auth/register", json=invalid_email_data)

        data = response.json()
        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_register_missing_email_returns_422(self, client: AsyncClient):
        """이메일 누락 시 422를 반환한다"""
        response = await client.post("/v1/auth/register", json={"password": "SecurePass123"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password_returns_422(self, client: AsyncClient):
        """비밀번호 누락 시 422를 반환한다"""
        response = await client.post("/v1/auth/register", json={"email": "test@example.com"})

        assert response.status_code == 422
