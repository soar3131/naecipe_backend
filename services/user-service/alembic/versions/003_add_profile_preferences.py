"""Add user_profiles and taste_preferences tables

Revision ID: 003
Revises: 002
Create Date: 2025-12-10

SPEC-003: 사용자 프로필 및 취향 설정
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_profiles and taste_preferences tables"""
    # 1. user_profiles 테이블 생성
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("profile_image_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "dietary_restrictions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "allergies",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "cuisine_preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("skill_level", sa.Integer(), nullable=True),
        sa.Column("household_size", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        # CHECK 제약: skill_level 1-5
        sa.CheckConstraint("skill_level >= 1 AND skill_level <= 5", name="ck_user_profiles_skill_level"),
        # CHECK 제약: household_size 1-20
        sa.CheckConstraint("household_size >= 1 AND household_size <= 20", name="ck_user_profiles_household_size"),
    )

    # user_profiles 인덱스
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    # 2. taste_preferences 테이블 생성
    op.create_table(
        "taste_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False, server_default="overall"),
        sa.Column("sweetness", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("saltiness", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("spiciness", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sourness", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "category", name="uq_taste_preferences_user_category"),
        # CHECK 제약: 맛 취향 값 1-5
        sa.CheckConstraint("sweetness >= 1 AND sweetness <= 5", name="ck_taste_preferences_sweetness"),
        sa.CheckConstraint("saltiness >= 1 AND saltiness <= 5", name="ck_taste_preferences_saltiness"),
        sa.CheckConstraint("spiciness >= 1 AND spiciness <= 5", name="ck_taste_preferences_spiciness"),
        sa.CheckConstraint("sourness >= 1 AND sourness <= 5", name="ck_taste_preferences_sourness"),
    )

    # taste_preferences 인덱스
    op.create_index("ix_taste_preferences_user_id", "taste_preferences", ["user_id"])
    op.create_index(
        "ix_taste_preferences_user_category",
        "taste_preferences",
        ["user_id", "category"],
        unique=True,
    )

    # 3. 기존 사용자에 대해 기본 UserProfile 레코드 생성
    op.execute("""
        INSERT INTO user_profiles (id, user_id, display_name)
        SELECT gen_random_uuid(), id, ''
        FROM users
        WHERE id NOT IN (SELECT user_id FROM user_profiles)
    """)


def downgrade() -> None:
    """Drop user_profiles and taste_preferences tables"""
    # taste_preferences 인덱스 삭제
    op.drop_index("ix_taste_preferences_user_category", table_name="taste_preferences")
    op.drop_index("ix_taste_preferences_user_id", table_name="taste_preferences")

    # taste_preferences 테이블 삭제
    op.drop_table("taste_preferences")

    # user_profiles 인덱스 삭제
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")

    # user_profiles 테이블 삭제
    op.drop_table("user_profiles")
