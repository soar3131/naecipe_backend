"""
프로필 서비스 레이어
SPEC-003: 사용자 프로필 및 취향 설정
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.models.user import User
from user_service.models.user_profile import UserProfile
from user_service.schemas.profile import ProfileData, ProfileUpdateRequest


class ProfileService:
    """사용자 프로필 관리 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: str) -> Optional[ProfileData]:
        """사용자 프로필 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            ProfileData if found, None otherwise
        """
        # User와 함께 Profile 조회
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Profile이 없으면 자동 생성
        profile = user.profile
        if not profile:
            profile = await self._create_default_profile(user_id)

        return ProfileData(
            id=user.id,
            email=user.email,
            displayName=profile.display_name or user.email.split("@")[0],
            profileImageUrl=profile.profile_image_url,
            createdAt=user.created_at,
            updatedAt=profile.updated_at,
        )

    async def update_profile(
        self,
        user_id: str,
        data: ProfileUpdateRequest,
    ) -> Optional[ProfileData]:
        """사용자 프로필 수정

        Args:
            user_id: 사용자 UUID
            data: 수정할 프로필 데이터

        Returns:
            Updated ProfileData if found, None otherwise
        """
        # User 확인
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Profile 조회 또는 생성
        profile = user.profile
        if not profile:
            profile = await self._create_default_profile(user_id)

        # 제공된 필드만 업데이트 (partial update)
        if data.display_name is not None:
            profile.display_name = data.display_name
        if data.profile_image_url is not None:
            profile.profile_image_url = data.profile_image_url

        await self.db.flush()
        await self.db.refresh(profile)

        return ProfileData(
            id=user.id,
            email=user.email,
            displayName=profile.display_name or user.email.split("@")[0],
            profileImageUrl=profile.profile_image_url,
            createdAt=user.created_at,
            updatedAt=profile.updated_at,
        )

    async def _create_default_profile(self, user_id: str) -> UserProfile:
        """기본 프로필 생성

        Args:
            user_id: 사용자 UUID

        Returns:
            생성된 UserProfile
        """
        profile = UserProfile(
            user_id=user_id,
            display_name="",
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def ensure_profile_exists(self, user_id: str) -> UserProfile:
        """프로필 존재 보장 (없으면 생성)

        Args:
            user_id: 사용자 UUID

        Returns:
            UserProfile
        """
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = await self._create_default_profile(user_id)

        return profile
