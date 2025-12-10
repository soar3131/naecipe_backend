"""
Users 모듈 SQLAlchemy 모델

User, UserProfile, TastePreference, OAuthAccount 모델을 정의합니다.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base

if TYPE_CHECKING:
    pass


# ==========================================================================
# Enums
# ==========================================================================


class UserStatus(str, enum.Enum):
    """사용자 계정 상태"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LOCKED = "LOCKED"


class OAuthProvider(str, enum.Enum):
    """OAuth 제공자 유형"""

    KAKAO = "kakao"
    GOOGLE = "google"
    NAVER = "naver"


# ==========================================================================
# User 모델
# ==========================================================================


class User(Base):
    """사용자 인증 모델"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount",
        back_populates="user",
        lazy="selectin",
    )
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        lazy="selectin",
    )
    taste_preferences: Mapped[list["TastePreference"]] = relationship(
        "TastePreference",
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """계정 활성 상태 확인"""
        return self.status == UserStatus.ACTIVE

    @property
    def is_locked(self) -> bool:
        """계정 잠금 상태 확인"""
        if self.status != UserStatus.LOCKED:
            return False
        if self.locked_until is None:
            return True
        return datetime.now(self.locked_until.tzinfo) < self.locked_until


# ==========================================================================
# UserProfile 모델
# ==========================================================================


class UserProfile(Base):
    """사용자 프로필 모델 - User와 1:1 관계"""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )
    profile_image_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    dietary_restrictions: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    allergies: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    cuisine_preferences: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
    )
    skill_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    household_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
    )

    def __repr__(self) -> str:
        return f"<UserProfile(id={self.id}, user_id={self.user_id}, display_name={self.display_name})>"


# ==========================================================================
# TastePreference 모델
# ==========================================================================


class TastePreference(Base):
    """맛 취향 모델 - User와 1:N 관계 (카테고리별)"""

    __tablename__ = "taste_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "category", name="uq_taste_preferences_user_category"
        ),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="overall",
    )
    sweetness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    saltiness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    spiciness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    sourness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="taste_preferences",
    )

    def __repr__(self) -> str:
        return f"<TastePreference(id={self.id}, user_id={self.user_id}, category={self.category})>"

    def to_dict(self) -> dict:
        """취향 값을 딕셔너리로 반환"""
        return {
            "sweetness": self.sweetness,
            "saltiness": self.saltiness,
            "spiciness": self.spiciness,
            "sourness": self.sourness,
        }


# ==========================================================================
# OAuthAccount 모델
# ==========================================================================


class OAuthAccount(Base):
    """소셜 로그인 OAuth 계정 모델"""

    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[OAuthProvider] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    provider_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_accounts_provider_user"
        ),
        UniqueConstraint(
            "user_id", "provider", name="uq_oauth_accounts_user_provider"
        ),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"
