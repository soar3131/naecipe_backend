"""
레시피(Recipe) 모델

원본 레시피 정보를 관리합니다.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipe_service.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from recipe_service.models.chef import Chef
    from recipe_service.models.ingredient import RecipeIngredient
    from recipe_service.models.step import CookingStep
    from recipe_service.models.tag import RecipeTag


class Recipe(Base, TimestampMixin):
    """
    레시피 모델

    크롤링으로 수집된 원본 레시피 정보
    """

    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # 요리사 참조 (nullable - 저자 불명인 경우)
    chef_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chefs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 기본 정보
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="레시피 제목",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="레시피 설명",
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="썸네일 이미지 URL",
    )
    video_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="영상 URL",
    )

    # 조리 정보
    prep_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="준비 시간 (분)",
    )
    cook_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="조리 시간 (분)",
    )
    servings: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="인분",
    )
    difficulty: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="난이도 (easy, medium, hard)",
    )

    # 출처 정보
    source_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        index=True,
        comment="원본 소스 URL",
    )
    source_platform: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="출처 플랫폼 (youtube, instagram, blog, naver)",
    )

    # 노출/인기도
    exposure_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        index=True,
        comment="노출 점수 (인기도 정렬용)",
    )
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="조회수",
    )

    # 상태
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="활성 상태",
    )

    # 관계
    chef: Mapped["Chef | None"] = relationship(
        "Chef",
        back_populates="recipes",
        lazy="joined",
    )
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RecipeIngredient.order_index",
    )
    steps: Mapped[list["CookingStep"]] = relationship(
        "CookingStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CookingStep.step_number",
    )
    recipe_tags: Mapped[list["RecipeTag"]] = relationship(
        "RecipeTag",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def total_time_minutes(self) -> int | None:
        """총 소요 시간"""
        if self.prep_time_minutes is None and self.cook_time_minutes is None:
            return None
        return (self.prep_time_minutes or 0) + (self.cook_time_minutes or 0)

    @property
    def tags(self) -> list["Tag"]:
        """태그 목록"""
        from recipe_service.models.tag import Tag

        return [rt.tag for rt in self.recipe_tags if rt.tag]
