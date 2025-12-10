"""Initial schema for recipe service

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-12-10

레시피 서비스 초기 데이터베이스 스키마
- Chef, ChefPlatform: 요리사 및 플랫폼 정보
- Recipe, RecipeIngredient, CookingStep: 레시피 핵심 모델
- Tag, RecipeTag: 태그 시스템
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # 요리사 (Chef) 테이블
    # =========================================================================
    op.create_table(
        "chefs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_normalized", sa.String(100), nullable=False),
        sa.Column("profile_image_url", sa.Text, nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("specialty", sa.String(50), nullable=True),
        sa.Column("recipe_count", sa.Integer, nullable=False, default=0),
        sa.Column("total_views", sa.BigInteger, nullable=False, default=0),
        sa.Column("avg_rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("is_verified", sa.Boolean, nullable=False, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # 인덱스: 이름 정규화 검색
    op.create_index(
        "ix_chefs_name_normalized",
        "chefs",
        ["name_normalized"],
    )

    # 인덱스: 전문 분야
    op.create_index(
        "ix_chefs_specialty",
        "chefs",
        ["specialty"],
    )

    # 인덱스: 인기 요리사 정렬
    op.create_index(
        "ix_chefs_popularity",
        "chefs",
        ["recipe_count", "total_views"],
    )

    # =========================================================================
    # 요리사 플랫폼 (ChefPlatform) 테이블
    # =========================================================================
    op.create_table(
        "chef_platforms",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "chef_id",
            sa.String(36),
            sa.ForeignKey("chefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform_name", sa.String(50), nullable=False),
        sa.Column("platform_url", sa.Text, nullable=False),
        sa.Column("channel_id", sa.String(100), nullable=True),
        sa.Column("subscriber_count", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # 유니크 제약: 요리사당 플랫폼 중복 방지
    op.create_unique_constraint(
        "uq_chef_platform",
        "chef_platforms",
        ["chef_id", "platform_name"],
    )

    # 인덱스: chef_id로 조회
    op.create_index(
        "ix_chef_platforms_chef_id",
        "chef_platforms",
        ["chef_id"],
    )

    # =========================================================================
    # 태그 (Tag) 테이블
    # =========================================================================
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("category", sa.String(30), nullable=True),
        sa.Column("usage_count", sa.Integer, nullable=False, default=0),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 인덱스: 카테고리별 조회
    op.create_index(
        "ix_tags_category",
        "tags",
        ["category"],
    )

    # 인덱스: 사용 빈도 정렬
    op.create_index(
        "ix_tags_usage_count",
        "tags",
        ["usage_count"],
    )

    # =========================================================================
    # 레시피 (Recipe) 테이블
    # =========================================================================
    op.create_table(
        "recipes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "chef_id",
            sa.String(36),
            sa.ForeignKey("chefs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("title_normalized", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("video_url", sa.Text, nullable=True),
        sa.Column("prep_time_minutes", sa.Integer, nullable=True),
        sa.Column("cook_time_minutes", sa.Integer, nullable=True),
        sa.Column("servings", sa.Integer, nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("source_platform", sa.String(50), nullable=True),
        sa.Column("exposure_score", sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column("view_count", sa.BigInteger, nullable=False, default=0),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    # 인덱스: 요리사별 레시피
    op.create_index(
        "ix_recipes_chef_id",
        "recipes",
        ["chef_id"],
    )

    # 인덱스: 제목 검색
    op.create_index(
        "ix_recipes_title_normalized",
        "recipes",
        ["title_normalized"],
    )

    # 인덱스: 인기 레시피 정렬
    op.create_index(
        "ix_recipes_exposure_score",
        "recipes",
        ["exposure_score", "view_count"],
    )

    # 인덱스: 활성 레시피 필터
    op.create_index(
        "ix_recipes_is_active",
        "recipes",
        ["is_active"],
    )

    # 인덱스: 최신 레시피 정렬
    op.create_index(
        "ix_recipes_created_at",
        "recipes",
        ["created_at"],
    )

    # 인덱스: 난이도 필터
    op.create_index(
        "ix_recipes_difficulty",
        "recipes",
        ["difficulty"],
    )

    # =========================================================================
    # 레시피 재료 (RecipeIngredient) 테이블
    # =========================================================================
    op.create_table(
        "recipe_ingredients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recipe_id",
            sa.String(36),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_normalized", sa.String(100), nullable=False),
        sa.Column("amount", sa.String(50), nullable=True),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("preparation", sa.String(100), nullable=True),
        sa.Column("is_optional", sa.Boolean, nullable=False, default=False),
        sa.Column("group_name", sa.String(50), nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, default=0),
    )

    # 인덱스: recipe_id로 조회
    op.create_index(
        "ix_recipe_ingredients_recipe_id",
        "recipe_ingredients",
        ["recipe_id"],
    )

    # 인덱스: 정렬 순서
    op.create_index(
        "ix_recipe_ingredients_order",
        "recipe_ingredients",
        ["recipe_id", "order_index"],
    )

    # =========================================================================
    # 조리 단계 (CookingStep) 테이블
    # =========================================================================
    op.create_table(
        "cooking_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recipe_id",
            sa.String(36),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("tip", sa.Text, nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
    )

    # 유니크 제약: 레시피당 단계 번호 중복 방지
    op.create_unique_constraint(
        "uq_recipe_step_number",
        "cooking_steps",
        ["recipe_id", "step_number"],
    )

    # 인덱스: recipe_id로 조회
    op.create_index(
        "ix_cooking_steps_recipe_id",
        "cooking_steps",
        ["recipe_id"],
    )

    # =========================================================================
    # 레시피-태그 연결 (RecipeTag) 테이블
    # =========================================================================
    op.create_table(
        "recipe_tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recipe_id",
            sa.String(36),
            sa.ForeignKey("recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.String(36),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 유니크 제약: 레시피-태그 중복 방지
    op.create_unique_constraint(
        "uq_recipe_tag",
        "recipe_tags",
        ["recipe_id", "tag_id"],
    )

    # 인덱스: recipe_id로 조회
    op.create_index(
        "ix_recipe_tags_recipe_id",
        "recipe_tags",
        ["recipe_id"],
    )

    # 인덱스: tag_id로 조회
    op.create_index(
        "ix_recipe_tags_tag_id",
        "recipe_tags",
        ["tag_id"],
    )


def downgrade() -> None:
    # 역순으로 삭제
    op.drop_table("recipe_tags")
    op.drop_table("cooking_steps")
    op.drop_table("recipe_ingredients")
    op.drop_table("recipes")
    op.drop_table("tags")
    op.drop_table("chef_platforms")
    op.drop_table("chefs")
