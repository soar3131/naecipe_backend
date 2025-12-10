# Quickstart: 원본 레시피 검색

**Branch**: `005-recipe-search` | **Date**: 2025-12-10

이 문서는 레시피 검색 기능의 통합 시나리오를 설명합니다.

---

## Prerequisites

1. Recipe Service 실행 중 (`http://localhost:8001`)
2. PostgreSQL 데이터베이스 연결 완료
3. Redis 캐시 연결 완료 (선택적)
4. 테스트용 레시피 데이터 존재

---

## Integration Scenarios

### Scenario 1: 기본 키워드 검색

사용자가 "김치"로 검색하여 관련 레시피를 찾습니다.

```bash
# 요청
curl -X GET "http://localhost:8001/recipes/search?q=김치"

# 응답
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "김치찌개",
      "description": "얼큰하고 맛있는 김치찌개",
      "thumbnail_url": "https://images.naecipe.com/recipes/kimchi-jjigae.jpg",
      "prep_time_minutes": 10,
      "cook_time_minutes": 30,
      "difficulty": "easy",
      "exposure_score": 85.5,
      "chef": {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "name": "백종원",
        "profile_image_url": "https://images.naecipe.com/chefs/baek.jpg"
      },
      "tags": [
        {"id": "770e8400-e29b-41d4-a716-446655440000", "name": "한식", "category": "cuisine"}
      ],
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "next_cursor": "eyJzIjoicmVsZXZhbmNlIiwidiI6ODUuNSwiaS4uLiI=",
  "has_more": true,
  "total_count": null
}
```

### Scenario 2: 필터링 검색

쉬운 난이도, 30분 이하 조리시간, 한식 태그로 필터링합니다.

```bash
# 요청
curl -X GET "http://localhost:8001/recipes/search?difficulty=easy&max_cook_time=30&tag=한식"

# 응답
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "계란말이",
      "description": "간단하고 맛있는 계란말이",
      "cook_time_minutes": 15,
      "difficulty": "easy",
      "exposure_score": 78.2,
      "chef": {...},
      "tags": [
        {"id": "...", "name": "한식", "category": "cuisine"},
        {"id": "...", "name": "반찬", "category": "dish_type"}
      ],
      ...
    }
  ],
  "next_cursor": null,
  "has_more": false,
  "total_count": null
}
```

### Scenario 3: 요리사로 검색

특정 요리사의 레시피를 검색합니다.

```bash
# 요리사 ID로 필터링
curl -X GET "http://localhost:8001/recipes/search?chef_id=660e8400-e29b-41d4-a716-446655440000"

# 요리사 이름으로 검색 (키워드)
curl -X GET "http://localhost:8001/recipes/search?q=백종원"
```

### Scenario 4: 정렬 옵션 적용

```bash
# 최신순 정렬
curl -X GET "http://localhost:8001/recipes/search?sort=latest"

# 조리시간순 정렬
curl -X GET "http://localhost:8001/recipes/search?sort=cook_time"

# 인기순 정렬
curl -X GET "http://localhost:8001/recipes/search?sort=popularity"
```

### Scenario 5: 무한 스크롤 페이지네이션

```bash
# 첫 번째 페이지
curl -X GET "http://localhost:8001/recipes/search?q=김치&limit=20"
# 응답: next_cursor = "abc123...", has_more = true

# 두 번째 페이지
curl -X GET "http://localhost:8001/recipes/search?q=김치&limit=20&cursor=abc123..."
# 응답: next_cursor = "def456...", has_more = true

# 마지막 페이지
curl -X GET "http://localhost:8001/recipes/search?q=김치&limit=20&cursor=def456..."
# 응답: next_cursor = null, has_more = false
```

---

## Error Handling

### 검색어 길이 초과

```bash
# 요청 (100자 초과 검색어)
curl -X GET "http://localhost:8001/recipes/search?q=<101자_이상_검색어>"

# 응답 (400 Bad Request)
{
  "error": {
    "code": "INVALID_SEARCH_QUERY",
    "message": "검색어는 100자 이하여야 합니다.",
    "details": {
      "field": "q",
      "max_length": 100
    }
  }
}
```

### 잘못된 정렬 옵션

```bash
# 요청
curl -X GET "http://localhost:8001/recipes/search?sort=unknown"

# 응답 (400 Bad Request)
{
  "error": {
    "code": "INVALID_SORT_OPTION",
    "message": "유효하지 않은 정렬 옵션입니다.",
    "details": {
      "provided": "unknown",
      "allowed": ["relevance", "latest", "cook_time", "popularity"]
    }
  }
}
```

### 잘못된 필터 값

```bash
# 요청 (음수 조리시간)
curl -X GET "http://localhost:8001/recipes/search?max_cook_time=-10"

# 응답 (400 Bad Request)
{
  "error": {
    "code": "INVALID_FILTER_VALUE",
    "message": "조리시간은 1분 이상이어야 합니다.",
    "details": {
      "field": "max_cook_time",
      "min_value": 1
    }
  }
}
```

---

## Code Examples

### Python (httpx)

```python
import httpx

async def search_recipes(
    keyword: str | None = None,
    difficulty: str | None = None,
    max_cook_time: int | None = None,
    tag: str | None = None,
    chef_id: str | None = None,
    sort: str = "relevance",
    cursor: str | None = None,
    limit: int = 20,
):
    """레시피 검색 API 호출"""
    params = {
        "q": keyword,
        "difficulty": difficulty,
        "max_cook_time": max_cook_time,
        "tag": tag,
        "chef_id": chef_id,
        "sort": sort,
        "cursor": cursor,
        "limit": limit,
    }
    # None 값 제거
    params = {k: v for k, v in params.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8001/recipes/search",
            params=params,
        )
        response.raise_for_status()
        return response.json()


# 사용 예시
async def main():
    # 기본 검색
    result = await search_recipes(keyword="김치")
    print(f"검색 결과: {len(result['items'])}개")

    # 필터링 검색
    result = await search_recipes(
        keyword="찌개",
        difficulty="easy",
        max_cook_time=30,
    )

    # 페이지네이션
    result = await search_recipes(keyword="김치", limit=10)
    while result["has_more"]:
        result = await search_recipes(
            keyword="김치",
            limit=10,
            cursor=result["next_cursor"],
        )
        print(f"다음 페이지: {len(result['items'])}개")
```

### JavaScript (fetch)

```javascript
async function searchRecipes(params = {}) {
  const queryParams = new URLSearchParams();

  if (params.q) queryParams.set('q', params.q);
  if (params.difficulty) queryParams.set('difficulty', params.difficulty);
  if (params.maxCookTime) queryParams.set('max_cook_time', params.maxCookTime);
  if (params.tag) queryParams.set('tag', params.tag);
  if (params.chefId) queryParams.set('chef_id', params.chefId);
  if (params.sort) queryParams.set('sort', params.sort);
  if (params.cursor) queryParams.set('cursor', params.cursor);
  if (params.limit) queryParams.set('limit', params.limit);

  const response = await fetch(
    `http://localhost:8001/recipes/search?${queryParams}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error.message);
  }

  return response.json();
}

// 사용 예시
async function main() {
  // 기본 검색
  const result = await searchRecipes({ q: '김치' });
  console.log(`검색 결과: ${result.items.length}개`);

  // 무한 스크롤
  let cursor = null;
  let allItems = [];

  do {
    const page = await searchRecipes({
      q: '김치',
      limit: 20,
      cursor,
    });
    allItems = allItems.concat(page.items);
    cursor = page.next_cursor;
  } while (cursor);

  console.log(`전체 결과: ${allItems.length}개`);
}
```

---

## Performance Testing

### 응답 시간 측정

```bash
# 캐시 미스 (첫 번째 요청)
time curl -s "http://localhost:8001/recipes/search?q=김치" > /dev/null

# 캐시 히트 (두 번째 요청)
time curl -s "http://localhost:8001/recipes/search?q=김치" > /dev/null
```

### 부하 테스트 (hey)

```bash
# 100 동시 사용자, 1000 요청
hey -n 1000 -c 100 "http://localhost:8001/recipes/search?q=김치"

# 목표: p99 < 200ms, RPS > 1000
```

---

## Cache Behavior

### 캐시 확인 (Redis CLI)

```bash
# 검색 캐시 키 조회
redis-cli KEYS "search:recipes:*"

# 특정 캐시 TTL 확인
redis-cli TTL "search:recipes:abc123..."

# 캐시 무효화 (테스트용)
redis-cli DEL "search:recipes:abc123..."

# 전체 검색 캐시 무효화
redis-cli KEYS "search:recipes:*" | xargs redis-cli DEL
```

---

## Troubleshooting

### 검색 결과가 없음

1. `is_active = TRUE`인 레시피가 있는지 확인
2. 검색어가 제목/설명/재료명/요리사명에 포함되는지 확인
3. 필터 조건을 모두 만족하는 레시피가 있는지 확인

```sql
-- 활성 레시피 수 확인
SELECT COUNT(*) FROM recipes WHERE is_active = TRUE;

-- 검색어 매칭 확인
SELECT title, description FROM recipes
WHERE is_active = TRUE
  AND (title ILIKE '%김치%' OR description ILIKE '%김치%');
```

### 응답이 느림

1. 인덱스 존재 여부 확인
2. 쿼리 실행 계획 확인
3. Redis 캐시 연결 상태 확인

```sql
-- 인덱스 확인
SELECT indexname FROM pg_indexes WHERE tablename = 'recipes';

-- 쿼리 실행 계획
EXPLAIN ANALYZE
SELECT * FROM recipes
WHERE is_active = TRUE AND title ILIKE '%김치%'
ORDER BY exposure_score DESC
LIMIT 20;
```

### 커서 오류

1. 커서가 올바른 형식(base64)인지 확인
2. 커서의 정렬 기준이 현재 요청과 일치하는지 확인
3. 커서가 만료되지 않았는지 확인 (데이터 변경으로 무효화)

---

## Related Specs

- [SPEC-004: 원본 레시피 기본 CRUD](../004-recipe-basic-crud/spec.md) - 레시피/요리사 기본 CRUD
- [SPEC-014: Elasticsearch 검색 서비스](../014-elasticsearch/spec.md) - Phase 2 검색 고도화
