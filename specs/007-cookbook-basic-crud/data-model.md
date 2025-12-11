# Data Model: 레시피북 기본 CRUD

**Feature Branch**: `007-cookbook-basic-crud`
**Created**: 2025-12-11

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│      User       │       │      Cookbook       │       │   SavedRecipe   │
│─────────────────│       │─────────────────────│       │─────────────────│
│ id (PK)         │──1:N──│ id (PK)             │──1:N──│ id (PK)         │
│ email           │       │ user_id (FK)        │       │ cookbook_id(FK) │
│ ...             │       │ name                │       │ recipe_id (FK)  │
└─────────────────┘       │ description         │       │ ...             │
                          │ cover_image_url     │       └─────────────────┘
                          │ sort_order          │              │
                          │ is_default          │              │
                          │ created_at          │              N
                          │ updated_at          │              │
                          └─────────────────────┘              ▼
                                                      ┌─────────────────┐
                                                      │     Recipe      │
                                                      │─────────────────│
                                                      │ id (PK)         │
                                                      │ title           │
                                                      │ ...             │
                                                      └─────────────────┘
```

## Entities

### Cookbook (레시피북)

사용자가 레시피를 분류하고 저장하는 컨테이너입니다.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK (users.id), NOT NULL, INDEX | 소유 사용자 |
| name | VARCHAR(100) | NOT NULL | 레시피북 이름 |
| description | TEXT | NULLABLE | 레시피북 설명 |
| cover_image_url | VARCHAR(500) | NULLABLE | 커버 이미지 URL |
| sort_order | INTEGER | NOT NULL, DEFAULT 0 | 정렬 순서 (오름차순) |
| is_default | BOOLEAN | NOT NULL, DEFAULT FALSE | 기본 레시피북 여부 |
| created_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW() | 생성 시각 |
| updated_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW() | 수정 시각 |

**Indexes**:
- `idx_cookbooks_user_id` on `user_id`
- `idx_cookbooks_user_sort` on `(user_id, sort_order)`

**Constraints**:
- `fk_cookbooks_user` FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
- `uq_cookbooks_user_default` UNIQUE (user_id) WHERE is_default = TRUE (Partial Unique Index)

### SavedRecipe (저장된 레시피) - 참조용

> 상세 구현은 SPEC-008에서 진행. 이 스펙에서는 cookbook_id FK 관계만 정의.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| cookbook_id | UUID | FK (cookbooks.id), NOT NULL, INDEX | 소속 레시피북 |
| recipe_id | UUID | FK (recipes.id), NOT NULL, INDEX | 원본 레시피 |
| ... | ... | ... | SPEC-008에서 추가 정의 |

**Constraints**:
- `fk_saved_recipes_cookbook` FOREIGN KEY (cookbook_id) REFERENCES cookbooks(id) ON DELETE CASCADE

## Relationships

### User ↔ Cookbook (1:N)

- 한 사용자는 여러 레시피북을 가질 수 있음
- 사용자 삭제 시 모든 레시피북 CASCADE 삭제
- 각 사용자는 정확히 하나의 기본 레시피북(is_default=true)을 가짐

### Cookbook ↔ SavedRecipe (1:N)

- 한 레시피북은 여러 저장된 레시피를 포함
- 레시피북 삭제 시 모든 저장된 레시피 CASCADE 삭제

## Business Rules

### 기본 레시피북 자동 생성

1. 사용자가 처음 레시피북 목록 조회 또는 레시피 저장 시도 시:
   - 레시피북이 없으면 "내 레시피북" 자동 생성
   - `is_default = TRUE`, `sort_order = 0`

2. 기본 레시피북 제약:
   - 삭제 불가 (API에서 차단)
   - 이름/설명/커버 이미지 수정은 가능

### 정렬 순서 (sort_order)

- 새 레시피북 생성 시: 현재 최대 sort_order + 1
- 순서 변경 API: 전달된 순서대로 1부터 재할당
- 기본 레시피북: sort_order 변경 가능 (첫 번째가 아니어도 됨)

### 이름 검증

- 최소 1자, 최대 100자
- 앞뒤 공백 자동 제거 (trim)
- 동일 사용자의 중복 이름 허용 (unique 제약 없음)

## Migration Notes

### Alembic Migration

```python
# 주요 마이그레이션 내용
def upgrade():
    op.create_table(
        'cookbooks',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('cover_image_url', sa.String(500), nullable=True),
        sa.Column('sort_order', sa.Integer, nullable=False, default=0),
        sa.Column('is_default', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Indexes
    op.create_index('idx_cookbooks_user_id', 'cookbooks', ['user_id'])
    op.create_index('idx_cookbooks_user_sort', 'cookbooks', ['user_id', 'sort_order'])

    # Partial unique index for default cookbook
    op.execute('''
        CREATE UNIQUE INDEX uq_cookbooks_user_default
        ON cookbooks (user_id)
        WHERE is_default = TRUE
    ''')
```
