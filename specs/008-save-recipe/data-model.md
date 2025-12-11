# Data Model: 레시피 저장

**Feature Branch**: `008-save-recipe`
**Date**: 2025-12-11

## Entity Relationship Diagram

```
┌──────────────┐       ┌───────────────┐       ┌──────────────┐
│   Cookbook   │       │  SavedRecipe  │       │    Recipe    │
├──────────────┤       ├───────────────┤       ├──────────────┤
│ id (PK)      │───1:N─│ id (PK)       │───N:1─│ id (PK)      │
│ user_id (FK) │       │ cookbook_id   │       │ title        │
│ name         │       │ orig_recipe_id│       │ thumbnail_url│
│ is_default   │       │ active_ver_id │       │ description  │
│ sort_order   │       │ memo          │       │ chef_id      │
│ ...          │       │ cook_count    │       │ ...          │
└──────────────┘       │ personal_rating│       └──────────────┘
                       │ last_cooked_at │
                       │ created_at    │
                       │ updated_at    │
                       └───────────────┘
                              │
                              │ (SPEC-009)
                              ▼ 1:N
                       ┌───────────────┐
                       │RecipeVariation│
                       │  (Future)     │
                       └───────────────┘
```

## Entities

### SavedRecipe

사용자가 레시피북에 저장한 원본 레시피에 대한 참조

#### 속성

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | NO | uuid4() | Primary Key |
| `cookbook_id` | UUID | NO | - | FK → cookbooks.id (CASCADE) |
| `original_recipe_id` | UUID | YES | - | FK → recipes.id (SET NULL) |
| `active_version_id` | UUID | YES | NULL | FK → recipe_variations.id (SPEC-009) |
| `memo` | TEXT | YES | NULL | 개인 메모 (max 1000자) |
| `cook_count` | INTEGER | NO | 0 | 조리 횟수 |
| `personal_rating` | DECIMAL(2,1) | YES | NULL | 개인 평점 (0.0-5.0) |
| `last_cooked_at` | TIMESTAMPTZ | YES | NULL | 마지막 조리 일시 |
| `created_at` | TIMESTAMPTZ | NO | now() | 생성 시각 |
| `updated_at` | TIMESTAMPTZ | NO | now() | 수정 시각 |

#### 제약조건

| Constraint | Type | Columns | Description |
|------------|------|---------|-------------|
| `pk_saved_recipes` | PRIMARY KEY | id | - |
| `fk_saved_recipes_cookbook` | FOREIGN KEY | cookbook_id → cookbooks.id | ON DELETE CASCADE |
| `fk_saved_recipes_recipe` | FOREIGN KEY | original_recipe_id → recipes.id | ON DELETE SET NULL |
| `uq_saved_recipes_cookbook_recipe` | UNIQUE | (cookbook_id, original_recipe_id) | 중복 저장 방지 |
| `idx_saved_recipes_cookbook` | INDEX | cookbook_id | 목록 조회 최적화 |
| `idx_saved_recipes_recipe` | INDEX | original_recipe_id | 원본 레시피별 조회 |
| `idx_saved_recipes_created_at` | INDEX | created_at | 정렬 최적화 |

#### 관계

| Relation | Type | Target | On Delete |
|----------|------|--------|-----------|
| cookbook | N:1 | Cookbook | CASCADE |
| original_recipe | N:1 | Recipe | SET NULL |
| active_version | N:1 | RecipeVariation | SET NULL (SPEC-009) |
| variations | 1:N | RecipeVariation | CASCADE (SPEC-009) |

## SQLAlchemy Model

```python
# app/cookbooks/models.py

from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DECIMAL, DateTime, ForeignKey, Index, Integer,
    Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base, TimestampMixin


class SavedRecipe(Base, TimestampMixin):
    """
    저장된 레시피 모델

    사용자가 레시피북에 저장한 원본 레시피에 대한 참조
    """

    __tablename__ = "saved_recipes"
    __table_args__ = (
        UniqueConstraint(
            "cookbook_id", "original_recipe_id",
            name="uq_saved_recipes_cookbook_recipe"
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
        nullable=True,  # 원본 레시피 삭제 시 SET NULL 허용
        comment="원본 레시피 ID",
    )
    active_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        # ForeignKey 는 SPEC-009에서 추가
        nullable=True,
        comment="현재 활성 보정 레시피 버전 ID",
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
        lazy="selectin",
    )
    original_recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        lazy="joined",
    )
    # active_version 관계는 SPEC-009에서 추가
```

## Alembic Migration

```python
# alembic/versions/xxx_create_saved_recipes_table.py

"""create saved_recipes table

Revision ID: xxx
Revises: yyy (007-cookbook 마이그레이션)
Create Date: 2025-12-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'xxx'
down_revision = 'yyy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'saved_recipes',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('cookbook_id', UUID(as_uuid=False),
                  sa.ForeignKey('cookbooks.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('original_recipe_id', UUID(as_uuid=False),
                  sa.ForeignKey('recipes.id', ondelete='SET NULL'),
                  nullable=True),  # 원본 레시피 삭제 시 SET NULL 허용
        sa.Column('active_version_id', UUID(as_uuid=False), nullable=True),
        sa.Column('memo', sa.Text, nullable=True),
        sa.Column('cook_count', sa.Integer, nullable=False, default=0),
        sa.Column('personal_rating', sa.DECIMAL(2, 1), nullable=True),
        sa.Column('last_cooked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(),
                  nullable=False),
        sa.UniqueConstraint('cookbook_id', 'original_recipe_id',
                           name='uq_saved_recipes_cookbook_recipe'),
    )

    op.create_index('idx_saved_recipes_cookbook', 'saved_recipes', ['cookbook_id'])
    op.create_index('idx_saved_recipes_recipe', 'saved_recipes', ['original_recipe_id'])
    op.create_index('idx_saved_recipes_created_at', 'saved_recipes', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_saved_recipes_created_at', table_name='saved_recipes')
    op.drop_index('idx_saved_recipes_recipe', table_name='saved_recipes')
    op.drop_index('idx_saved_recipes_cookbook', table_name='saved_recipes')
    op.drop_table('saved_recipes')
```

## Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `memo` | max_length=1000 | "Memo must not exceed 1000 characters" |
| `personal_rating` | 0.0 ≤ value ≤ 5.0 | "Rating must be between 0.0 and 5.0" |
| `cookbook_id` | must exist & owned by user | CookbookNotFoundError |
| `original_recipe_id` | must exist | RecipeNotFoundError |
| (cookbook_id, recipe_id) | must be unique | RecipeAlreadySavedError (409) |

## Future Extensions (SPEC-009, SPEC-010)

### RecipeVariation (SPEC-009)
- `active_version_id` FK 추가
- `variations` 1:N 관계 추가
- SavedRecipe 삭제 시 RecipeVariation CASCADE 삭제

### Cooking Feedback (SPEC-010)
- `cook_count` 증가
- `personal_rating` 설정
- `last_cooked_at` 갱신
