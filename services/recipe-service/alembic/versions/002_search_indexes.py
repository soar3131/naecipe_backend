"""Search indexes for recipe search optimization

Revision ID: 002_search_indexes
Revises: 001_initial_schema
Create Date: 2024-12-10

검색 성능 최적화를 위한 인덱스 추가
- 정렬용 복합 인덱스
- 텍스트 패턴 검색용 인덱스
- 필터링용 인덱스
"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_search_indexes"
down_revision: str = "001_initial_schema"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # =========================================================================
    # 정렬용 복합 인덱스
    # =========================================================================

    # 조리시간 정렬용 (cook_time)
    op.execute("""
        CREATE INDEX idx_recipes_cook_time_sort
        ON recipes (cook_time_minutes ASC NULLS LAST, id ASC)
        WHERE is_active = TRUE
    """)

    # 인기순 정렬용 (popularity)
    op.execute("""
        CREATE INDEX idx_recipes_view_count_sort
        ON recipes (view_count DESC, id DESC)
        WHERE is_active = TRUE
    """)

    # 최신순 정렬용 (latest)
    op.execute("""
        CREATE INDEX idx_recipes_created_at_sort
        ON recipes (created_at DESC, id DESC)
        WHERE is_active = TRUE
    """)

    # =========================================================================
    # 텍스트 패턴 검색용 인덱스
    # =========================================================================

    # 재료명 LIKE 검색 최적화
    op.execute("""
        CREATE INDEX idx_recipe_ingredients_name_pattern
        ON recipe_ingredients (name varchar_pattern_ops)
    """)

    # 요리사명 LIKE 검색 최적화
    op.execute("""
        CREATE INDEX idx_chefs_name_pattern
        ON chefs (name varchar_pattern_ops)
    """)

    # 레시피 제목 LIKE 검색 최적화
    op.execute("""
        CREATE INDEX idx_recipes_title_pattern
        ON recipes (title varchar_pattern_ops)
        WHERE is_active = TRUE
    """)

    # =========================================================================
    # 필터링용 인덱스
    # =========================================================================

    # 난이도 필터용
    op.execute("""
        CREATE INDEX idx_recipes_difficulty
        ON recipes (difficulty)
        WHERE is_active = TRUE
    """)

    # 조리시간 범위 필터용
    op.execute("""
        CREATE INDEX idx_recipes_cook_time_range
        ON recipes (cook_time_minutes)
        WHERE is_active = TRUE AND cook_time_minutes IS NOT NULL
    """)


def downgrade() -> None:
    # 필터링 인덱스 삭제
    op.execute("DROP INDEX IF EXISTS idx_recipes_cook_time_range")
    op.execute("DROP INDEX IF EXISTS idx_recipes_difficulty")

    # 텍스트 패턴 인덱스 삭제
    op.execute("DROP INDEX IF EXISTS idx_recipes_title_pattern")
    op.execute("DROP INDEX IF EXISTS idx_chefs_name_pattern")
    op.execute("DROP INDEX IF EXISTS idx_recipe_ingredients_name_pattern")

    # 정렬용 인덱스 삭제
    op.execute("DROP INDEX IF EXISTS idx_recipes_created_at_sort")
    op.execute("DROP INDEX IF EXISTS idx_recipes_view_count_sort")
    op.execute("DROP INDEX IF EXISTS idx_recipes_cook_time_sort")
