"""
요리사(Chef) 모델

요리사 정보와 플랫폼 정보를 관리합니다.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipe_service.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from recipe_service.models.recipe import Recipe


class Chef(Base, TimestampMixin):
    """
    요리사 모델

    셰프, 인플루언서, 유튜버, 블로거 등 레시피를 만든 원작자 정보
    """

    __tablename__ = "chefs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="요리사 이름 (예: 백종원, 승우아빠)",
    )
    name_normalized: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="검색용 정규화된 이름",
    )
    profile_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="프로필 이미지 URL",
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="요리사 소개",
    )
    specialty: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="전문 분야 (예: 한식, 양식)",
    )

    # 집계 필드 (캐싱용)
    recipe_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="등록된 레시피 수",
    )
    total_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="총 조회수",
    )
    avg_rating: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="평균 평점",
    )

    # 상태
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="인증된 요리사 여부",
    )

    # 관계
    platforms: Mapped[list["ChefPlatform"]] = relationship(
        "ChefPlatform",
        back_populates="chef",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe",
        back_populates="chef",
        lazy="selectin",
    )


class ChefPlatform(Base, TimestampMixin):
    """
    요리사 플랫폼 정보

    멀티 플랫폼 지원 (YouTube, Instagram, Blog 등)
    """

    __tablename__ = "chef_platforms"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    chef_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chefs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="플랫폼 종류 (youtube, instagram, blog, naver)",
    )
    platform_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="플랫폼 내 채널/계정 ID",
    )
    platform_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="플랫폼 프로필/채널 URL",
    )
    subscriber_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="구독자/팔로워 수",
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="마지막 동기화 시각",
    )

    # 관계
    chef: Mapped["Chef"] = relationship(
        "Chef",
        back_populates="platforms",
    )
