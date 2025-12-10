"""Integration tests for registration flow"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.models.user import User, UserStatus


class TestRegisterIntegration:
    """Integration tests for registration flow"""

    @pytest.mark.asyncio
    async def test_register_creates_user_in_database(
        self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict
    ):
        """회원가입 시 데이터베이스에 사용자가 생성된다"""
        response = await client.post("/v1/auth/register", json=valid_user_data)

        assert response.status_code == 201

        # Verify user exists in database
        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == valid_user_data["email"]

    @pytest.mark.asyncio
    async def test_register_hashes_password(
        self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict
    ):
        """비밀번호가 해시되어 저장된다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        user = result.scalar_one()

        # Password should be hashed, not plain text
        assert user.password_hash != valid_user_data["password"]
        assert user.password_hash.startswith("$2b$")  # bcrypt prefix

    @pytest.mark.asyncio
    async def test_register_sets_active_status(
        self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict
    ):
        """새 사용자는 ACTIVE 상태로 생성된다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        user = result.scalar_one()

        assert user.status == UserStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_register_sets_timestamps(
        self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict
    ):
        """created_at과 updated_at이 설정된다"""
        await client.post("/v1/auth/register", json=valid_user_data)

        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        user = result.scalar_one()

        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_register_returns_user_id(self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict):
        """응답에 포함된 ID가 데이터베이스의 사용자 ID와 일치한다"""
        response = await client.post("/v1/auth/register", json=valid_user_data)

        response_id = response.json()["id"]

        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        user = result.scalar_one()

        assert str(user.id) == response_id

    @pytest.mark.asyncio
    async def test_register_duplicate_email_does_not_create_second_user(
        self, client: AsyncClient, test_session: AsyncSession, valid_user_data: dict
    ):
        """중복 이메일 가입 시도 시 두 번째 사용자가 생성되지 않는다"""
        # First registration
        await client.post("/v1/auth/register", json=valid_user_data)

        # Try duplicate registration
        await client.post("/v1/auth/register", json=valid_user_data)

        # Should only have one user
        result = await test_session.execute(select(User).where(User.email == valid_user_data["email"]))
        users = result.scalars().all()

        assert len(users) == 1

    @pytest.mark.asyncio
    async def test_register_email_is_case_insensitive(self, client: AsyncClient, valid_user_data: dict):
        """이메일 대소문자 구분 없이 중복 검사한다"""
        # Register with lowercase
        await client.post("/v1/auth/register", json=valid_user_data)

        # Try with uppercase
        uppercase_data = {**valid_user_data, "email": valid_user_data["email"].upper()}
        response = await client.post("/v1/auth/register", json=uppercase_data)

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_password_policy_min_length(self, client: AsyncClient):
        """비밀번호는 최소 8자 이상이어야 한다"""
        response = await client.post(
            "/v1/auth/register",
            json={"email": "test@example.com", "password": "Short1"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_policy_requires_letter_and_number(self, client: AsyncClient):
        """비밀번호는 문자와 숫자를 포함해야 한다"""
        # Only letters
        response = await client.post(
            "/v1/auth/register",
            json={"email": "test@example.com", "password": "onlyletters"},
        )
        assert response.status_code == 422

        # Only numbers
        response = await client.post(
            "/v1/auth/register",
            json={"email": "test2@example.com", "password": "12345678"},
        )
        assert response.status_code == 422
