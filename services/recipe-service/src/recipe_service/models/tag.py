"""
태그(Tag) 모델

레시피의 태그 정보를 관리합니다.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipe_service.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from recipe_service.models.recipe import Recipe


class Tag(Base, TimestampMixin):
    """
    태그 모델

    레시피 분류용 태그
    카테고리: dish_type, cuisine, meal_type, cooking_method, dietary
    """

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="태그명 (예: 한식, 찌개, 비건)",
    )
    category: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
        comment="태그 카테고리 (dish_type, cuisine, meal_type, cooking_method, dietary)",
    )
    display_order: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="표시 순서",
    )

    # 관계
    recipe_tags: Mapped[list["RecipeTag"]] = relationship(
        "RecipeTag",
        back_populates="tag",
        cascade="all, delete-orphan",
    )


class RecipeTag(Base):
    """
    레시피-태그 연결 테이블

    다대다 관계 구현
    """

    __tablename__ = "recipe_tags"
    __table_args__ = (
        UniqueConstraint("recipe_id", "tag_id", name="uq_recipe_tag"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    recipe_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 관계
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="recipe_tags",
    )
    tag: Mapped["Tag"] = relationship(
        "Tag",
        back_populates="recipe_tags",
        lazy="joined",
    )
