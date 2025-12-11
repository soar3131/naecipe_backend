# Research: 유사 레시피 추천

**Feature**: 006-similar-recipe-recommendation
**Date**: 2025-12-11
**Status**: Completed

## 1. 유사도 계산 알고리즘

### 1.1 알고리즘 비교

| 알고리즘 | 장점 | 단점 | 적합성 |
|---------|------|------|--------|
| **Jaccard Similarity** | 집합 기반, 직관적 | 가중치 미반영 | ✅ 태그/재료 유사도에 적합 |
| **Cosine Similarity** | 방향 유사도, TF-IDF 호환 | 벡터 표현 필요 | 🔶 Phase 2 벡터 검색 |
| **SQL COUNT 기반** | 단순, 빠름, 추가 인프라 불필요 | 정교함 부족 | ✅ MVP에 적합 |

### 1.2 결정: SQL 기반 유사도 계산

**선택 근거**:
1. Constitution VII (Simplicity) 준수 - 추가 인프라 없이 구현
2. Knowledge 모듈 벡터 검색은 SPEC-013 이후 통합 예정
3. PostgreSQL의 강력한 집합 연산 활용 가능

**유사도 계산 공식**:
```
similarity_score = (
    tag_overlap_weight * tag_similarity +
    ingredient_overlap_weight * ingredient_similarity +
    cooking_similarity_weight * cooking_similarity
)

where:
- tag_similarity = COUNT(shared_tags) / COUNT(union_tags)
- ingredient_similarity = COUNT(shared_ingredients) / COUNT(union_ingredients)
- cooking_similarity = 1 - |difficulty_diff| / 3 - |time_diff| / max_time
```

**가중치 설정**:
- 태그 유사도: 0.4 (가장 직관적)
- 재료 유사도: 0.4 (요리 특성 반영)
- 조리법 유사도: 0.2 (난이도, 시간)

### 1.3 대안 검토: 벡터 유사도 (Phase 2)

**Knowledge 모듈 통합 시 (SPEC-013 이후)**:
- pgvector 기반 벡터 유사도 검색
- 레시피 임베딩 (제목, 설명, 재료 텍스트)
- 하이브리드 검색: SQL 필터링 + 벡터 유사도 리랭킹

**마이그레이션 전략**:
1. 현재 SQL 기반 유사도로 MVP 출시
2. SPEC-013 완료 후 `SimilarRecipeService` 확장
3. Feature flag로 점진적 전환

---

## 2. 캐싱 전략

### 2.1 캐시 키 패턴

| 캐시 키 | TTL | 용도 |
|--------|-----|------|
| `recipes:{id}:similar` | 10분 | 유사 레시피 목록 |
| `recipes:{id}:same-chef` | 10분 | 같은 요리사 레시피 |
| `recipes:{id}:related-tags` | 10분 | 태그 기반 관련 레시피 |
| `recipes:{id}:category-popular:{category}` | 10분 | 카테고리 인기 레시피 |

### 2.2 캐시 무효화 정책

**무효화 트리거**:
1. 레시피 수정/삭제 시: 해당 레시피의 모든 추천 캐시 삭제
2. 태그 변경 시: 관련 레시피의 `related-tags` 캐시 삭제
3. 요리사 정보 변경 시: 해당 요리사의 `same-chef` 캐시 삭제

**무효화 패턴**:
```python
# 레시피 수정 시
async def invalidate_similar_caches(recipe_id: str):
    cache = await get_redis_cache()
    patterns = [
        f"recipes:{recipe_id}:similar",
        f"recipes:{recipe_id}:same-chef",
        f"recipes:{recipe_id}:related-tags",
        f"recipes:{recipe_id}:category-popular:*",
    ]
    for pattern in patterns:
        keys = await cache.keys(pattern)
        for key in keys:
            await cache.delete(key)
```

### 2.3 성능 목표 달성 전략

**응답 시간 목표**:
- 캐시 히트: < 50ms
- 캐시 미스: < 300ms

**최적화 방법**:
1. **Eager Loading**: 레시피, 요리사, 태그를 한 번에 조회
2. **LIMIT + Scoring**: 상위 N개만 계산하여 반환
3. **인덱스 최적화**: `recipe_tags`, `recipe_ingredients` 테이블 인덱스 활용

---

## 3. SQL 쿼리 패턴

### 3.1 태그 기반 유사도 쿼리

```sql
-- 태그 겹침 기반 유사 레시피 조회
WITH source_tags AS (
    SELECT tag_id FROM recipe_tags WHERE recipe_id = :recipe_id
),
tag_similarity AS (
    SELECT
        r.id,
        COUNT(DISTINCT rt.tag_id) as shared_tags,
        (SELECT COUNT(*) FROM source_tags) as source_tag_count
    FROM recipes r
    JOIN recipe_tags rt ON r.id = rt.recipe_id
    WHERE rt.tag_id IN (SELECT tag_id FROM source_tags)
      AND r.id != :recipe_id
      AND r.is_active = true
    GROUP BY r.id
)
SELECT
    r.*,
    ts.shared_tags::float / GREATEST(ts.source_tag_count, 1) as tag_score
FROM recipes r
JOIN tag_similarity ts ON r.id = ts.id
ORDER BY tag_score DESC, r.exposure_score DESC
LIMIT :limit;
```

### 3.2 재료 기반 유사도 쿼리

```sql
-- 재료명 겹침 기반 유사 레시피 조회
WITH source_ingredients AS (
    SELECT LOWER(name) as name FROM recipe_ingredients WHERE recipe_id = :recipe_id
),
ingredient_similarity AS (
    SELECT
        r.id,
        COUNT(DISTINCT LOWER(ri.name)) as shared_ingredients,
        (SELECT COUNT(*) FROM source_ingredients) as source_count
    FROM recipes r
    JOIN recipe_ingredients ri ON r.id = ri.recipe_id
    WHERE LOWER(ri.name) IN (SELECT name FROM source_ingredients)
      AND r.id != :recipe_id
      AND r.is_active = true
    GROUP BY r.id
)
SELECT
    r.*,
    ris.shared_ingredients::float / GREATEST(ris.source_count, 1) as ingredient_score
FROM recipes r
JOIN ingredient_similarity ris ON r.id = ris.id
ORDER BY ingredient_score DESC, r.exposure_score DESC
LIMIT :limit;
```

### 3.3 통합 유사도 쿼리 (최종)

```sql
-- 태그 + 재료 + 조리법 통합 유사도
WITH source_recipe AS (
    SELECT id, difficulty, cook_time_minutes
    FROM recipes WHERE id = :recipe_id
),
source_tags AS (
    SELECT tag_id FROM recipe_tags WHERE recipe_id = :recipe_id
),
source_ingredients AS (
    SELECT LOWER(name) as name FROM recipe_ingredients WHERE recipe_id = :recipe_id
),
similarity_scores AS (
    SELECT
        r.id,
        -- 태그 유사도 (0.4)
        0.4 * COALESCE(
            (SELECT COUNT(DISTINCT rt.tag_id)::float
             FROM recipe_tags rt
             WHERE rt.recipe_id = r.id AND rt.tag_id IN (SELECT tag_id FROM source_tags))
            / NULLIF((SELECT COUNT(*) FROM source_tags), 0),
            0
        ) +
        -- 재료 유사도 (0.4)
        0.4 * COALESCE(
            (SELECT COUNT(DISTINCT LOWER(ri.name))::float
             FROM recipe_ingredients ri
             WHERE ri.recipe_id = r.id AND LOWER(ri.name) IN (SELECT name FROM source_ingredients))
            / NULLIF((SELECT COUNT(*) FROM source_ingredients), 0),
            0
        ) +
        -- 조리법 유사도 (0.2): 난이도 + 시간
        0.2 * (
            CASE
                WHEN r.difficulty = (SELECT difficulty FROM source_recipe) THEN 0.5
                ELSE 0.25
            END +
            CASE
                WHEN ABS(COALESCE(r.cook_time_minutes, 0) - COALESCE((SELECT cook_time_minutes FROM source_recipe), 0)) < 15 THEN 0.5
                WHEN ABS(COALESCE(r.cook_time_minutes, 0) - COALESCE((SELECT cook_time_minutes FROM source_recipe), 0)) < 30 THEN 0.25
                ELSE 0
            END
        ) as similarity_score
    FROM recipes r
    WHERE r.id != :recipe_id AND r.is_active = true
)
SELECT
    r.*,
    ss.similarity_score
FROM recipes r
JOIN similarity_scores ss ON r.id = ss.id
WHERE ss.similarity_score > 0.1  -- 최소 유사도 임계값
ORDER BY ss.similarity_score DESC, r.exposure_score DESC
LIMIT :limit;
```

---

## 4. 페이지네이션 패턴

### 4.1 커서 기반 페이지네이션

기존 `CursorData` 패턴 확장:

```python
@dataclass
class SimilarityCursor:
    similarity_score: float
    exposure_score: float
    recipe_id: str

def encode_similarity_cursor(cursor: SimilarityCursor) -> str:
    data = {
        "sim": cursor.similarity_score,
        "exp": cursor.exposure_score,
        "id": cursor.recipe_id
    }
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
```

### 4.2 기본 limit 및 최대 제한

- **기본 limit**: 10개
- **최대 limit**: 50개
- **FR-014 준수**: 레시피당 기본 10개 제한

---

## 5. 엣지 케이스 처리

### 5.1 태그 없는 레시피

```python
if not source_recipe.recipe_tags:
    # 재료 기반 유사도만 계산
    # 조리법(난이도, 시간) 유사도도 포함
    return await self._find_similar_by_ingredients_only(recipe_id, limit)
```

### 5.2 요리사 없는 레시피

```python
if not source_recipe.chef_id:
    # same-chef API: 빈 목록 반환
    return SimilarRecipeListResponse(
        items=[],
        next_cursor=None,
        has_more=False,
    )
```

### 5.3 유사 레시피 없음

```python
if not similar_recipes:
    # 유사도 임계값 0으로 낮추고 인기순 fallback
    return await self._get_fallback_popular(category, limit)
```

---

## 6. 성능 벤치마크 기준

### 6.1 테스트 데이터셋

- 레시피: 10,000개
- 레시피당 평균 태그: 5개
- 레시피당 평균 재료: 10개

### 6.2 목표 성능

| 시나리오 | 목표 응답 시간 | 측정 방법 |
|---------|---------------|----------|
| 캐시 히트 | < 50ms | Redis GET 시간 |
| 캐시 미스 (태그 기반) | < 200ms | SQL 쿼리 실행 시간 |
| 캐시 미스 (통합 유사도) | < 300ms | SQL 쿼리 실행 시간 |
| 같은 요리사 | < 100ms | 단순 필터 쿼리 |

### 6.3 인덱스 요구사항

```sql
-- 기존 인덱스 확인
CREATE INDEX idx_recipe_tags_recipe_id ON recipe_tags(recipe_id);
CREATE INDEX idx_recipe_tags_tag_id ON recipe_tags(tag_id);
CREATE INDEX idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX idx_recipes_chef_id ON recipes(chef_id);
CREATE INDEX idx_recipes_is_active ON recipes(is_active);

-- 추가 인덱스 (필요시)
CREATE INDEX idx_recipe_ingredients_name_lower ON recipe_ingredients(LOWER(name));
```

---

## 7. 결정 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| 유사도 알고리즘 | SQL 기반 Jaccard | Constitution VII, 추가 인프라 불필요 |
| 가중치 | 태그 0.4, 재료 0.4, 조리법 0.2 | 요리 특성 반영 밸런스 |
| 캐시 TTL | 10분 | FR-013 준수 |
| 최소 유사도 | 0.1 (10%) | 너무 관련 없는 결과 제외 |
| 기본 limit | 10개 | FR-014 준수 |
| 페이지네이션 | 커서 기반 | 기존 패턴 일관성 |

---

## 8. 향후 개선 사항 (Phase 2)

1. **벡터 유사도 통합**: SPEC-013 완료 후 pgvector 활용
2. **개인화**: 사용자 취향 기반 가중치 조절
3. **A/B 테스트**: 유사도 알고리즘 성능 비교
4. **ML 기반 랭킹**: 클릭률/저장률 기반 학습
