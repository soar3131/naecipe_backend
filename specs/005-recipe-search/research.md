# Research: 원본 레시피 검색

**Branch**: `005-recipe-search` | **Date**: 2025-12-10 | **Status**: Complete

---

## Overview

레시피 검색 기능 구현을 위한 기술 리서치 결과입니다. Phase 1 MVP에서는 PostgreSQL ILIKE 기반 검색을, Phase 2에서는 Elasticsearch 연동을 계획합니다.

---

## Decision 1: 검색 알고리즘 선택

### Decision

**PostgreSQL ILIKE 부분 일치 검색** (Phase 1 MVP)

### Rationale

1. **추가 인프라 불필요**: Elasticsearch 없이 PostgreSQL만으로 구현 가능
2. **충분한 성능**: 10만 건 이하 레시피에서 인덱스 활용 시 p99 200ms 이내 달성 가능
3. **빠른 구현**: SQLAlchemy 기존 코드 재사용, 별도 인덱싱 파이프라인 불필요
4. **점진적 확장**: Phase 2에서 Elasticsearch로 마이그레이션 용이

### Alternatives Considered

| 대안 | 장점 | 단점 | 기각 사유 |
|------|------|------|-----------|
| Elasticsearch | 전문 검색, 형태소 분석, 관련도 스코어링 | 인프라 추가, 인덱싱 파이프라인 필요 | Phase 2에서 구현 예정 |
| PostgreSQL Full-Text Search | GIN 인덱스, 한국어 지원 가능 | ts_vector 설정 복잡, 형태소 분석기 필요 | MVP 범위 초과 |
| Trigram (pg_trgm) | 유사도 기반 검색 | 대용량에서 성능 이슈, 인덱스 크기 증가 | MVP 요구사항 과잉 |

### Implementation Notes

```sql
-- 기본 검색 쿼리 (제목, 설명)
SELECT * FROM recipes
WHERE is_active = TRUE
  AND (title ILIKE '%keyword%' OR description ILIKE '%keyword%')
ORDER BY exposure_score DESC
LIMIT 20;

-- 재료명 검색 (JOIN)
SELECT DISTINCT r.* FROM recipes r
JOIN recipe_ingredients ri ON r.id = ri.recipe_id
WHERE r.is_active = TRUE
  AND ri.name ILIKE '%keyword%'
ORDER BY r.exposure_score DESC;

-- 요리사명 검색 (JOIN)
SELECT r.* FROM recipes r
JOIN chefs c ON r.chef_id = c.id
WHERE r.is_active = TRUE
  AND c.name ILIKE '%keyword%'
ORDER BY r.exposure_score DESC;
```

---

## Decision 2: 커서 기반 페이지네이션 구현

### Decision

**복합 키 커서 (exposure_score, id)** 를 사용한 keyset pagination

### Rationale

1. **일관성**: 실시간 데이터 변경에도 중복/누락 없음
2. **성능**: OFFSET 방식 대비 O(1) 성능 (인덱스 활용)
3. **무한 스크롤 지원**: 클라이언트에서 next_cursor만 전달하면 됨
4. **정렬 기준 확장 용이**: 정렬 필드 추가 시 커서 형식만 변경

### Alternatives Considered

| 대안 | 장점 | 단점 | 기각 사유 |
|------|------|------|-----------|
| OFFSET/LIMIT | 구현 간단 | 대용량에서 성능 저하, 데이터 변경 시 중복/누락 | 확장성 부족 |
| 페이지 번호 | UI 친화적 | 무한 스크롤에 부적합, 성능 이슈 | UX 요구사항 불일치 |

### Implementation Notes

**커서 인코딩 형식**:
```python
# 커서 = base64(json({score, id}))
import base64
import json

def encode_cursor(score: float, recipe_id: str) -> str:
    data = {"s": score, "i": recipe_id}
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

def decode_cursor(cursor: str) -> tuple[float, str]:
    data = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    return data["s"], data["i"]
```

**쿼리 조건**:
```sql
-- 다음 페이지 조회 (relevance = exposure_score DESC)
WHERE (exposure_score < :prev_score)
   OR (exposure_score = :prev_score AND id < :prev_id)
ORDER BY exposure_score DESC, id DESC
LIMIT :limit
```

**정렬별 커서 필드**:
| 정렬 | 커서 필드 | ORDER BY |
|------|----------|----------|
| relevance | (exposure_score, id) | exposure_score DESC, id DESC |
| latest | (created_at, id) | created_at DESC, id DESC |
| cook_time | (cook_time_minutes, id) | cook_time_minutes ASC, id ASC |
| popularity | (view_count, id) | view_count DESC, id DESC |

---

## Decision 3: 필터링 구현 방식

### Decision

**동적 쿼리 빌더** - SQLAlchemy 조건 조합

### Rationale

1. **유연성**: 다양한 필터 조합 지원
2. **타입 안전성**: SQLAlchemy ORM을 통한 파라미터 바인딩
3. **확장성**: 새 필터 추가 시 조건만 추가

### Implementation Notes

```python
def build_search_query(
    keyword: str | None,
    difficulty: str | None,
    max_cook_time: int | None,
    tag: str | None,
    chef_id: str | None,
    sort: str = "relevance",
    cursor: str | None = None,
    limit: int = 20,
) -> Select:
    stmt = select(Recipe).where(Recipe.is_active == True)

    # 키워드 검색 (제목, 설명, 재료명, 요리사명)
    if keyword:
        keyword_conditions = [
            Recipe.title.ilike(f"%{keyword}%"),
            Recipe.description.ilike(f"%{keyword}%"),
        ]
        # 재료명 서브쿼리
        ingredient_subq = (
            select(RecipeIngredient.recipe_id)
            .where(RecipeIngredient.name.ilike(f"%{keyword}%"))
            .distinct()
        )
        keyword_conditions.append(Recipe.id.in_(ingredient_subq))

        # 요리사명 서브쿼리
        chef_subq = (
            select(Recipe.id)
            .join(Chef)
            .where(Chef.name.ilike(f"%{keyword}%"))
        )
        keyword_conditions.append(Recipe.id.in_(chef_subq))

        stmt = stmt.where(or_(*keyword_conditions))

    # 필터링
    if difficulty:
        stmt = stmt.where(Recipe.difficulty == difficulty)
    if max_cook_time:
        stmt = stmt.where(Recipe.cook_time_minutes <= max_cook_time)
    if chef_id:
        stmt = stmt.where(Recipe.chef_id == chef_id)
    if tag:
        tag_subq = (
            select(RecipeTag.recipe_id)
            .join(Tag)
            .where(Tag.name == tag)
        )
        stmt = stmt.where(Recipe.id.in_(tag_subq))

    # 정렬 + 커서
    stmt = apply_sort_and_cursor(stmt, sort, cursor)

    return stmt.limit(limit + 1)  # +1 for has_more detection
```

---

## Decision 4: 캐싱 전략

### Decision

**검색 쿼리 해시 기반 Redis 캐싱** (TTL 5분)

### Rationale

1. **반복 검색 최적화**: 인기 검색어/필터 조합에 대한 빠른 응답
2. **DB 부하 감소**: 동일 쿼리 재실행 방지
3. **간단한 무효화**: TTL 기반 자동 만료 + 레시피 변경 시 전체 무효화

### Implementation Notes

**캐시 키 설계**:
```python
def get_search_cache_key(
    keyword: str | None,
    difficulty: str | None,
    max_cook_time: int | None,
    tag: str | None,
    chef_id: str | None,
    sort: str,
    cursor: str | None,
    limit: int,
) -> str:
    params = {
        "q": keyword or "",
        "d": difficulty or "",
        "t": max_cook_time or 0,
        "tag": tag or "",
        "c": chef_id or "",
        "s": sort,
        "cur": cursor or "",
        "l": limit,
    }
    hash_input = json.dumps(params, sort_keys=True)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:16]
    return f"search:recipes:{hash_value}"
```

**캐시 무효화 이벤트**:
| 이벤트 | 무효화 대상 |
|--------|------------|
| RecipeCreated | `search:recipes:*` (SCAN + DEL) |
| RecipeUpdated | `search:recipes:*` |
| RecipeDeleted | `search:recipes:*` |

---

## Decision 5: 정렬 옵션 구현

### Decision

**4가지 정렬 옵션 지원**: relevance, latest, cook_time, popularity

### Rationale

1. **relevance (기본값)**: exposure_score 기반으로 이미 인기도 반영
2. **latest**: 신규 레시피 발견 용이
3. **cook_time**: 시간 제약 있는 사용자용
4. **popularity**: 검증된 레시피 선호 사용자용

### Implementation Notes

| 정렬 옵션 | ORDER BY | 인덱스 필요 |
|----------|----------|------------|
| relevance | exposure_score DESC, id DESC | idx_recipes_exposure_score |
| latest | created_at DESC, id DESC | idx_recipes_created_at |
| cook_time | cook_time_minutes ASC NULLS LAST, id ASC | idx_recipes_cook_time |
| popularity | view_count DESC, id DESC | idx_recipes_view_count |

**필요 인덱스 추가**:
```sql
CREATE INDEX idx_recipes_cook_time ON recipes (cook_time_minutes ASC NULLS LAST, id ASC) WHERE is_active = TRUE;
CREATE INDEX idx_recipes_view_count ON recipes (view_count DESC, id DESC) WHERE is_active = TRUE;
```

---

## Decision 6: 검색어 보안 처리

### Decision

**Pydantic 검증 + SQLAlchemy 파라미터 바인딩**

### Rationale

1. **SQL Injection 방지**: SQLAlchemy ORM의 파라미터 바인딩 자동 처리
2. **입력 제한**: Pydantic으로 최대 길이, 허용 문자 검증
3. **XSS 방지**: 응답 시 HTML 이스케이프 (FastAPI 기본 제공)

### Implementation Notes

```python
from pydantic import BaseModel, Field, field_validator
import re

class SearchQueryParams(BaseModel):
    q: str | None = Field(None, max_length=100, description="검색 키워드")
    difficulty: str | None = Field(None, pattern="^(easy|medium|hard)$")
    max_cook_time: int | None = Field(None, ge=1, le=1440)
    tag: str | None = Field(None, max_length=50)
    chef_id: str | None = Field(None, pattern="^[a-f0-9-]{36}$")
    sort: str = Field("relevance", pattern="^(relevance|latest|cook_time|popularity)$")
    cursor: str | None = Field(None, max_length=200)
    limit: int = Field(20, ge=1, le=100)

    @field_validator("q")
    @classmethod
    def sanitize_keyword(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # 연속 공백 제거, 앞뒤 공백 제거
        v = re.sub(r"\s+", " ", v.strip())
        # 빈 문자열이면 None 반환
        return v if v else None
```

---

## Decision 7: 성능 최적화

### Decision

**복합 인덱스 + JOIN 최적화 + 선택적 COUNT 생략**

### Rationale

1. **복합 인덱스**: 정렬+커서 조건을 단일 인덱스로 처리
2. **JOIN 최적화**: 재료명/요리사명 검색 시 EXISTS 서브쿼리 사용
3. **COUNT 생략**: total_count는 항상 null (커서 페이지네이션에서 불필요)

### Implementation Notes

**인덱스 전략**:
```sql
-- 기존 인덱스 활용
idx_recipes_exposure_score (exposure_score DESC) WHERE is_active = TRUE
idx_recipes_created_at (created_at DESC)
idx_recipes_chef_id (chef_id)

-- 추가 인덱스
CREATE INDEX idx_recipes_cook_time ON recipes (cook_time_minutes ASC NULLS LAST, id ASC) WHERE is_active = TRUE;
CREATE INDEX idx_recipes_view_count ON recipes (view_count DESC, id DESC) WHERE is_active = TRUE;
CREATE INDEX idx_recipe_ingredients_name ON recipe_ingredients (name varchar_pattern_ops);
CREATE INDEX idx_chefs_name_search ON chefs (name varchar_pattern_ops);
```

**EXISTS 서브쿼리 최적화**:
```sql
-- 재료명 검색 (IN 대신 EXISTS)
WHERE EXISTS (
    SELECT 1 FROM recipe_ingredients ri
    WHERE ri.recipe_id = recipes.id
    AND ri.name ILIKE '%keyword%'
)
```

---

## Technical Context Summary

| 항목 | 결정 사항 |
|------|----------|
| 검색 알고리즘 | PostgreSQL ILIKE (Phase 1), Elasticsearch (Phase 2) |
| 페이지네이션 | 커서 기반 (keyset pagination) |
| 필터링 | 동적 쿼리 빌더 (SQLAlchemy) |
| 정렬 옵션 | relevance, latest, cook_time, popularity |
| 캐싱 | Redis 쿼리 해시 캐싱 (TTL 5분) |
| 보안 | Pydantic 검증 + SQLAlchemy 파라미터 바인딩 |
| 성능 목표 | p99 200ms 이하, 1000 RPS |

---

## Dependencies

- **SPEC-004 완료 필수**: chefs, recipes, recipe_ingredients, tags 테이블
- **Redis 7+**: 검색 결과 캐싱
- **PostgreSQL 15+**: ILIKE 검색, 인덱스

---

## Phase 2 Migration Plan (Elasticsearch)

Phase 2에서 Elasticsearch 연동 시 변경 사항:

1. **Search Service 연동**: recipe-service에서 search-service로 검색 위임
2. **인덱싱 파이프라인**: RecipeCreated/Updated 이벤트 소비 → ES 인덱싱
3. **한국어 형태소 분석**: nori 플러그인 적용
4. **BM25 스코어링**: relevance 정렬 시 검색어 관련도 반영
5. **자동완성**: edge ngram 필드 추가

현재 Phase 1 구현은 Phase 2 마이그레이션을 고려하여 Service Layer 추상화를 유지합니다.
