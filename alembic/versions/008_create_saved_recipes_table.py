"""create saved_recipes table

Revision ID: 008_create_saved_recipes
Revises: 007 (cookbooks)
Create Date: 2025-12-11

SPEC-008: 레시피 저장 (원본 레시피 → 레시피북)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "008_saved_recipes"
down_revision = None  # 이전 마이그레이션 ID로 교체 필요
branch_labels = None
depends_on = None


def upgrade() -> None:
    """saved_recipes 테이블 생성"""
    op.create_table(
        "saved_recipes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "cookbook_id",
            UUID(as_uuid=False),
            sa.ForeignKey("cookbooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "original_recipe_id",
            UUID(as_uuid=False),
            sa.ForeignKey("recipes.id", ondelete="SET NULL"),
            nullable=True,  # 원본 레시피 삭제 시 SET NULL 허용
        ),
        sa.Column("active_version_id", UUID(as_uuid=False), nullable=True),
        sa.Column("memo", sa.Text, nullable=True),
        sa.Column("cook_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("personal_rating", sa.DECIMAL(2, 1), nullable=True),
        sa.Column("last_cooked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "cookbook_id",
            "original_recipe_id",
            name="uq_saved_recipes_cookbook_recipe",
        ),
    )

    # 인덱스 생성
    op.create_index(
        "idx_saved_recipes_cookbook", "saved_recipes", ["cookbook_id"]
    )
    op.create_index(
        "idx_saved_recipes_recipe", "saved_recipes", ["original_recipe_id"]
    )
    op.create_index(
        "idx_saved_recipes_created_at", "saved_recipes", ["created_at"]
    )


def downgrade() -> None:
    """saved_recipes 테이블 삭제"""
    op.drop_index("idx_saved_recipes_created_at", table_name="saved_recipes")
    op.drop_index("idx_saved_recipes_recipe", table_name="saved_recipes")
    op.drop_index("idx_saved_recipes_cookbook", table_name="saved_recipes")
    op.drop_table("saved_recipes")
