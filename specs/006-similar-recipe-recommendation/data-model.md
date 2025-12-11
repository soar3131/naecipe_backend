# Data Model: 유사 레시피 추천

**Feature**: 006-similar-recipe-recommendation
**Date**: 2025-12-11
**Status**: Completed

## 1. 개요

이 기능은 **새로운 테이블을 생성하지 않습니다**. 기존 테이블의 관계를 활용하여 SQL 기반 유사도 계산을 수행합니다.

---

## 2. 사용되는 기존 엔티티

### 2.1 Recipe (레시피)

```
recipes 테이블
├── id: UUID (PK)
├── original_id: VARCHAR (원본 레시피 ID)
├── title: VARCHAR (레시피 제목)
├── description: TEXT (설명)
├── chef_id: UUID (FK → chefs.id)
├── difficulty: VARCHAR (난이도: easy, medium, hard)
├── cook_time_minutes: INTEGER (조리 시간, 분)
├── servings: INTEGER (인분)
├── category: VARCHAR (카테고리)
├── thumbnail_url: VARCHAR (썸네일 URL)
├── view_count: INTEGER (조회수)
├── exposure_score: FLOAT (노출 점수)
├── is_active: BOOLEAN (활성 상태)
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP
```

**유사도 계산에 사용되는 필드**:
- `chef_id`: 같은 요리사 레시피 조회
- `difficulty`: 조리법 유사도 (난이도 비교)
- `cook_time_minutes`: 조리법 유사도 (시간 비교)
- `category`: 카테고리 인기 레시피 조회
- `is_active`: 활성 레시피만 조회
- `exposure_score`: 정렬 기준 (유사도 동점 시)

### 2.2 Tag (태그)

```
tags 테이블
├── id: UUID (PK)
├── name: VARCHAR (태그명, UNIQUE)
├── slug: VARCHAR (URL 슬러그)
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP
```

### 2.3 RecipeTag (레시피-태그 관계)

```
recipe_tags 테이블
├── id: UUID (PK)
├── recipe_id: UUID (FK → recipes.id)
├── tag_id: UUID (FK → tags.id)
└── created_at: TIMESTAMP

인덱스:
├── idx_recipe_tags_recipe_id ON (recipe_id)
└── idx_recipe_tags_tag_id ON (tag_id)
```

**유사도 계산에 사용**:
- 태그 겹침 개수 계산
- Jaccard 유사도: `COUNT(shared_tags) / COUNT(union_tags)`

### 2.4 RecipeIngredient (레시피 재료)

```
recipe_ingredients 테이블
├── id: UUID (PK)
├── recipe_id: UUID (FK → recipes.id)
├── name: VARCHAR (재료명)
├── amount: VARCHAR (양)
├── unit: VARCHAR (단위)
├── order_index: INTEGER (순서)
└── created_at: TIMESTAMP

인덱스:
├── idx_recipe_ingredients_recipe_id ON (recipe_id)
└── idx_recipe_ingredients_name_lower ON (LOWER(name)) -- 추가 권장
```

**유사도 계산에 사용**:
- 재료명 겹침 개수 계산 (대소문자 무시)
- Jaccard 유사도: `COUNT(shared_ingredients) / COUNT(union_ingredients)`

### 2.5 Chef (요리사)

```
chefs 테이블
├── id: UUID (PK)
├── name: VARCHAR (요리사 이름)
├── description: TEXT (소개)
├── profile_image_url: VARCHAR (프로필 이미지)
├── platform: chef_platform ENUM (youtube, instagram, etc.)
├── platform_id: VARCHAR (플랫폼별 ID)
├── subscriber_count: INTEGER (구독자 수)
├── is_verified: BOOLEAN (인증 여부)
├── is_active: BOOLEAN (활성 상태)
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP
```

**유사도 계산에 사용**:
- 같은 요리사 레시피 조회 (chef_id 필터)

---

## 3. 엔티티 관계도 (ERD)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    Chef     │       │   Recipe    │       │    Tag      │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ chef_id (FK)│       │ id (PK)     │
│ name        │  1:N  │ id (PK)     │       │ name        │
│ platform    │       │ title       │       │ slug        │
└─────────────┘       │ difficulty  │       └──────┬──────┘
                      │ cook_time   │              │
                      │ category    │              │
                      └──────┬──────┘              │
                             │                     │
                     ┌───────┴────────┐            │
                     │                │            │
                     ▼                ▼            ▼
          ┌─────────────────┐  ┌─────────────────┐
          │RecipeIngredient │  │   RecipeTag     │
          ├─────────────────┤  ├─────────────────┤
          │ id (PK)         │  │ id (PK)         │
          │ recipe_id (FK)  │  │ recipe_id (FK)  │◄────┐
          │ name            │  │ tag_id (FK)     │─────┘
          │ amount          │  └─────────────────┘  M:N
          │ unit            │
          └─────────────────┘
```

---

## 4. 유사도 계산 데이터 흐름

### 4.1 태그 기반 유사도

```
Source Recipe (id)
       │
       ▼
┌─────────────────┐
│ recipe_tags     │ → source_tags (태그 ID 목록)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ recipe_tags     │ → 같은 태그를 가진 다른 레시피 찾기
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ COUNT + GROUP   │ → 태그 겹침 개수 계산
└────────┬────────┘
         │
         ▼
   tag_score = shared_count / source_count
```

### 4.2 재료 기반 유사도

```
Source Recipe (id)
       │
       ▼
┌─────────────────────┐
│ recipe_ingredients  │ → source_ingredients (재료명 목록, LOWER)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ recipe_ingredients  │ → 같은 재료를 가진 다른 레시피 찾기
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ COUNT + GROUP       │ → 재료 겹침 개수 계산
└────────┬────────────┘
         │
         ▼
   ingredient_score = shared_count / source_count
```

### 4.3 통합 유사도 점수

```
similarity_score = (
    0.4 × tag_score +
    0.4 × ingredient_score +
    0.2 × cooking_score
)

where cooking_score = (
    0.5 × difficulty_match +  # 난이도 일치: 0.5, 불일치: 0.25
    0.5 × time_proximity      # 시간 차이: <15분: 0.5, <30분: 0.25, else: 0
)
```

---

## 5. 인덱스 요구사항

### 5.1 기존 인덱스 (확인 필요)

```sql
-- recipe_tags 테이블
CREATE INDEX IF NOT EXISTS idx_recipe_tags_recipe_id ON recipe_tags(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_tags_tag_id ON recipe_tags(tag_id);

-- recipe_ingredients 테이블
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);

-- recipes 테이블
CREATE INDEX IF NOT EXISTS idx_recipes_chef_id ON recipes(chef_id);
CREATE INDEX IF NOT EXISTS idx_recipes_is_active ON recipes(is_active);
CREATE INDEX IF NOT EXISTS idx_recipes_category ON recipes(category);
```

### 5.2 권장 추가 인덱스

```sql
-- 재료명 대소문자 무시 검색 최적화
CREATE INDEX idx_recipe_ingredients_name_lower
    ON recipe_ingredients(LOWER(name));

-- 복합 인덱스: 활성 레시피 + 카테고리
CREATE INDEX idx_recipes_active_category
    ON recipes(is_active, category)
    WHERE is_active = true;

-- 복합 인덱스: 활성 레시피 + 노출 점수 (정렬 최적화)
CREATE INDEX idx_recipes_active_exposure
    ON recipes(is_active, exposure_score DESC)
    WHERE is_active = true;
```

---

## 6. 쿼리 패턴

### 6.1 유사 레시피 조회 (통합)

```sql
-- 핵심 쿼리: 태그 + 재료 + 조리법 유사도
WITH source_recipe AS (
    SELECT id, difficulty, cook_time_minutes
    FROM recipes WHERE id = :recipe_id
),
source_tags AS (
    SELECT tag_id FROM recipe_tags WHERE recipe_id = :recipe_id
),
source_ingredients AS (
    SELECT LOWER(name) as name FROM recipe_ingredients WHERE recipe_id = :recipe_id
)
SELECT
    r.*,
    similarity_score
FROM recipes r
JOIN (
    -- 유사도 계산 서브쿼리
) ss ON r.id = ss.id
WHERE r.id != :recipe_id
  AND r.is_active = true
  AND similarity_score > 0.1
ORDER BY similarity_score DESC, r.exposure_score DESC
LIMIT :limit;
```

### 6.2 같은 요리사 레시피

```sql
SELECT r.*
FROM recipes r
WHERE r.chef_id = (SELECT chef_id FROM recipes WHERE id = :recipe_id)
  AND r.id != :recipe_id
  AND r.is_active = true
ORDER BY r.exposure_score DESC
LIMIT :limit;
```

### 6.3 태그 기반 관련 레시피

```sql
WITH source_tags AS (
    SELECT tag_id FROM recipe_tags WHERE recipe_id = :recipe_id
)
SELECT r.*, COUNT(DISTINCT rt.tag_id) as shared_tags
FROM recipes r
JOIN recipe_tags rt ON r.id = rt.recipe_id
WHERE rt.tag_id IN (SELECT tag_id FROM source_tags)
  AND r.id != :recipe_id
  AND r.is_active = true
GROUP BY r.id
ORDER BY shared_tags DESC, r.exposure_score DESC
LIMIT :limit;
```

### 6.4 카테고리 인기 레시피

```sql
SELECT r.*
FROM recipes r
WHERE r.category = (SELECT category FROM recipes WHERE id = :recipe_id)
  AND r.id != :recipe_id
  AND r.is_active = true
ORDER BY r.view_count DESC, r.exposure_score DESC
LIMIT :limit;
```

---

## 7. 데이터 검증 규칙

| 필드 | 검증 규칙 | 에러 처리 |
|------|----------|----------|
| recipe_id | 유효한 UUID, 존재하는 레시피 | 404 Not Found |
| limit | 1 ≤ limit ≤ 50, 기본값 10 | 400 Bad Request |
| cursor | 유효한 Base64 인코딩 | 400 Bad Request |

---

## 8. 캐시 키 구조

```
recipes:{recipe_id}:similar           → 유사 레시피 목록
recipes:{recipe_id}:same-chef         → 같은 요리사 레시피
recipes:{recipe_id}:related-tags      → 태그 기반 관련 레시피
recipes:{recipe_id}:category-popular:{category} → 카테고리 인기 레시피
```

**TTL**: 10분 (600초)

---

## 9. 마이그레이션 필요 여부

**필요 없음** - 이 기능은 새로운 테이블이나 컬럼을 추가하지 않습니다.

권장 인덱스 추가는 선택적이며, 성능 모니터링 후 필요시 적용할 수 있습니다.

---

## 10. 향후 확장 (Phase 2)

SPEC-013 (Knowledge 모듈) 완료 후:

1. **레시피 임베딩 테이블 추가**:
   ```sql
   CREATE TABLE recipe_embeddings (
       id UUID PRIMARY KEY,
       recipe_id UUID REFERENCES recipes(id),
       embedding vector(1536),  -- pgvector
       created_at TIMESTAMP
   );
   ```

2. **벡터 유사도 검색**:
   ```sql
   SELECT r.*, 1 - (re.embedding <=> :query_embedding) as similarity
   FROM recipes r
   JOIN recipe_embeddings re ON r.id = re.recipe_id
   ORDER BY re.embedding <=> :query_embedding
   LIMIT :limit;
   ```

3. **하이브리드 검색**:
   - SQL 필터링 (활성, 카테고리) + 벡터 유사도 리랭킹
