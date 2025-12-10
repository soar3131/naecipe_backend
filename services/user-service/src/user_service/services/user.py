"""User service for user management operations"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.core.exceptions import EmailExistsError
from user_service.core.security import hash_password
from user_service.models.user import User, UserStatus
from user_service.models.user_profile import UserProfile
from user_service.schemas.auth import RegisterRequest
from user_service.schemas.user import RegisterResponse


class UserService:
    """Service for user management operations"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, request: RegisterRequest) -> RegisterResponse:
        """Create a new user with email and password

        Args:
            request: Registration request with email and password

        Returns:
            RegisterResponse with user id, email, and created_at

        Raises:
            EmailExistsError: If email already exists
        """
        # Normalize email to lowercase
        email = request.email.lower()

        # Check for duplicate email
        if await self._email_exists(email):
            raise EmailExistsError(email=email)

        # Hash password
        password_hash = hash_password(request.password)

        # Create user
        user = User(
            email=email,
            password_hash=password_hash,
            status=UserStatus.ACTIVE,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        # 프로필 자동 생성 (SPEC-003)
        profile = UserProfile(
            user_id=user.id,
            display_name="",
        )
        self.db.add(profile)
        await self.db.flush()

        return RegisterResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        )

    async def _email_exists(self, email: str) -> bool:
        """Check if email already exists (case-insensitive)

        Args:
            email: Email to check (should be lowercase)

        Returns:
            True if email exists, False otherwise
        """
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    async def get_user_by_email(self, email: str) -> User | None:
        """Get user by email

        Args:
            email: User email

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
