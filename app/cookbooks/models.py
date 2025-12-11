"""
Cookbooks 모듈 모델

레시피북 및 저장된 레시피 엔티티를 정의합니다.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    DECIMAL,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base, TimestampMixin


class Cookbook(Base, TimestampMixin):
    """
    레시피북 모델

    사용자가 레시피를 분류하고 저장하는 컨테이너
    """

    __tablename__ = "cookbooks"

    # Partial Unique Index는 Alembic 마이그레이션에서 직접 SQL로 생성
    # CREATE UNIQUE INDEX uq_cookbooks_user_default ON cookbooks (user_id) WHERE is_default = TRUE;

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="소유 사용자 ID",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="레시피북 이름",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="레시피북 설명",
    )
    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="커버 이미지 URL",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="정렬 순서 (오름차순)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="기본 레시피북 여부",
    )

    # 관계
    saved_recipes: Mapped[list["SavedRecipe"]] = relationship(
        "SavedRecipe",
        back_populates="cookbook",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SavedRecipe(Base, TimestampMixin):
    """
    저장된 레시피 모델

    사용자가 레시피북에 저장한 원본 레시피에 대한 참조
    """

    __tablename__ = "saved_recipes"
    __table_args__ = (
        UniqueConstraint(
            "cookbook_id",
            "original_recipe_id",
            name="uq_saved_recipes_cookbook_recipe",
        ),
        Index("idx_saved_recipes_cookbook", "cookbook_id"),
        Index("idx_saved_recipes_recipe", "original_recipe_id"),
        Index("idx_saved_recipes_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    cookbook_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("cookbooks.id", ondelete="CASCADE"),
        nullable=False,
        comment="소속 레시피북 ID",
    )
    original_recipe_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
        comment="원본 레시피 ID",
    )
    active_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        comment="현재 활성 보정 레시피 버전 ID (SPEC-009)",
    )
    memo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="개인 메모 (최대 1000자)",
    )
    cook_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="조리 횟수",
    )
    personal_rating: Mapped[Decimal | None] = mapped_column(
        DECIMAL(2, 1),
        nullable=True,
        comment="개인 평점 (0.0-5.0)",
    )
    last_cooked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="마지막 조리 일시",
    )

    # 관계
    cookbook: Mapped["Cookbook"] = relationship(
        "Cookbook",
        back_populates="saved_recipes",
    )
    original_recipe: Mapped["Recipe"] = relationship(  # type: ignore[name-defined]
        "Recipe",
        lazy="joined",
    )


# Partial Unique Index를 위한 DDL (Alembic 마이그레이션에서 사용)
# CREATE UNIQUE INDEX uq_cookbooks_user_default
# ON cookbooks (user_id)
# WHERE is_default = TRUE;
