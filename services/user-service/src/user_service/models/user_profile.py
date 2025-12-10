"""
UserProfile SQLAlchemy 모델
SPEC-003: 사용자 프로필 및 취향 설정
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_service.db.base import Base

if TYPE_CHECKING:
    from user_service.models.user import User


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
