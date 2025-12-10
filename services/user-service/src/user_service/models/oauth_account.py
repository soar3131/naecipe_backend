"""OAuthAccount SQLAlchemy model"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_service.db.base import Base


class OAuthProvider(str, enum.Enum):
    """OAuth provider types"""

    KAKAO = "kakao"
    GOOGLE = "google"
    NAVER = "naver"


class OAuthAccount(Base):
    """OAuth account model for social login"""

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
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")  # type: ignore[name-defined]

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_oauth_accounts_user_provider"),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, provider={self.provider}, user_id={self.user_id})>"
