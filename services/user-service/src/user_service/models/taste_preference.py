"""
TastePreference SQLAlchemy 모델
SPEC-003: 사용자 프로필 및 취향 설정
"""
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_service.db.base import Base

if TYPE_CHECKING:
    from user_service.models.user import User


class TastePreference(Base):
    """맛 취향 모델 - User와 1:N 관계 (카테고리별)"""

    __tablename__ = "taste_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_taste_preferences_user_category"),
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
