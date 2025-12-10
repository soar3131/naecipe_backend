"""
Recipes 모듈 모델

레시피, 요리사, 재료, 조리단계, 태그 모델을 정의합니다.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base, TimestampMixin


# ==========================================================================
# 요리사 (Chef) 모델
# ==========================================================================


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


# ==========================================================================
# 레시피 (Recipe) 모델
# ==========================================================================


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
        return [rt.tag for rt in self.recipe_tags if rt.tag]


# ==========================================================================
# 재료 (Ingredient) 모델
# ==========================================================================


class RecipeIngredient(Base):
    """
    레시피 재료 모델

    레시피에 포함된 재료 정보
    """

    __tablename__ = "recipe_ingredients"

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

    # 재료 정보
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="재료명",
    )
    amount: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="양 (예: 300, 1/2, 약간)",
    )
    unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="단위 (예: g, ml, 개, 큰술)",
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="부가 설명 (예: 다진 것, 잘게 썬 것)",
    )

    # 순서
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="표시 순서",
    )

    # 관계
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="ingredients",
    )

    @property
    def display_amount(self) -> str:
        """표시용 양"""
        if self.amount and self.unit:
            return f"{self.amount}{self.unit}"
        elif self.amount:
            return self.amount
        elif self.unit:
            return self.unit
        return ""


# ==========================================================================
# 조리 단계 (Cooking Step) 모델
# ==========================================================================


class CookingStep(Base):
    """
    조리 단계 모델

    레시피의 순차적인 조리 과정
    """

    __tablename__ = "cooking_steps"

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

    # 단계 정보
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="단계 번호 (1부터 시작)",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="단계 설명",
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="단계별 이미지 URL",
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="단계 소요 시간 (초)",
    )
    tip: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="조리 팁",
    )

    # 관계
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="steps",
    )

    @property
    def duration_minutes(self) -> int | None:
        """소요 시간 (분)"""
        if self.duration_seconds is None:
            return None
        return self.duration_seconds // 60


# ==========================================================================
# 태그 (Tag) 모델
# ==========================================================================


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
