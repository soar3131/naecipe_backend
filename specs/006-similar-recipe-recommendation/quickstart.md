# Quickstart: 유사 레시피 추천

**Feature**: 006-similar-recipe-recommendation
**Date**: 2025-12-11

## 1. 빠른 시작

### 1.1 사전 요구사항

- Docker Desktop 실행 중
- Python 3.11+
- Poetry 설치됨

### 1.2 환경 설정

```bash
# 1. 의존성 설치
poetry install

# 2. 인프라 시작
docker-compose up -d postgres redis

# 3. 데이터베이스 마이그레이션
poetry run alembic upgrade head

# 4. 서버 시작
poetry run uvicorn app.main:app --reload
```

---

## 2. API 사용 예제

### 2.1 유사 레시피 조회

```bash
# 기본 요청 (10개)
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/similar"

# 개수 지정
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/similar?limit=5"

# 페이지네이션
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/similar?cursor=eyJzaW0iOjAuODV9"
```

**응답 예시**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "돼지고기 김치찌개",
      "thumbnail_url": "https://example.com/thumb1.jpg",
      "difficulty": "medium",
      "cook_time_minutes": 30,
      "chef": {
        "id": "660e8400-e29b-41d4-a716-446655440001",
        "name": "백종원",
        "profile_image_url": "https://example.com/chef1.jpg"
      },
      "similarity_score": 0.85,
      "tags": [
        {"name": "한식", "slug": "korean"},
        {"name": "찌개", "slug": "stew"}
      ]
    }
  ],
  "next_cursor": "eyJzaW0iOjAuODUsImV4cCI6MTAwLCJpZCI6IjU1MGU4NDAwIn0=",
  "has_more": true
}
```

### 2.2 같은 요리사 레시피 조회

```bash
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/same-chef?limit=5"
```

**응답 예시**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "title": "백종원 볶음밥",
      "thumbnail_url": "https://example.com/thumb2.jpg",
      "difficulty": "easy",
      "cook_time_minutes": 15,
      "view_count": 50000,
      "tags": [
        {"name": "한식", "slug": "korean"}
      ]
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

### 2.3 태그 기반 관련 레시피 조회

```bash
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/related-by-tags?limit=5"
```

### 2.4 카테고리 인기 레시피 조회

```bash
curl -X GET "http://localhost:8000/api/v1/recipes/{recipe_id}/category-popular?limit=5"
```

---

## 3. 통합 테스트 시나리오

### 3.1 시나리오 1: 유사 레시피 조회 (캐시 미스)

**목적**: 캐시가 없을 때 SQL 쿼리로 유사도 계산 확인

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_similar_recipes_cache_miss(client: AsyncClient, sample_recipe):
    """캐시 미스 시 유사 레시피 조회 테스트"""
    # Given: 테스트 레시피 (태그 3개, 재료 5개)
    recipe_id = sample_recipe.id

    # When: 유사 레시피 조회
    response = await client.get(f"/api/v1/recipes/{recipe_id}/similar")

    # Then: 성공 응답
    assert response.status_code == 200
    data = response.json()

    # 응답 구조 검증
    assert "items" in data
    assert "next_cursor" in data
    assert "has_more" in data

    # 유사도 검증 (80% 이상 태그 겹침)
    for item in data["items"]:
        assert item["similarity_score"] >= 0.1
        assert "tags" in item
```

### 3.2 시나리오 2: 유사 레시피 조회 (캐시 히트)

**목적**: 두 번째 요청 시 캐시에서 결과 반환 확인

```python
@pytest.mark.asyncio
async def test_similar_recipes_cache_hit(client: AsyncClient, sample_recipe, redis_client):
    """캐시 히트 시 유사 레시피 조회 테스트"""
    recipe_id = sample_recipe.id

    # Given: 첫 번째 요청 (캐시 생성)
    response1 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
    assert response1.status_code == 200

    # When: 두 번째 요청 (캐시 히트)
    response2 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")

    # Then: 동일한 결과
    assert response2.status_code == 200
    assert response1.json() == response2.json()

    # 캐시 존재 확인
    cache_key = f"recipes:{recipe_id}:similar"
    cached = await redis_client.get(cache_key)
    assert cached is not None
```

### 3.3 시나리오 3: 같은 요리사 레시피 (요리사 없음)

**목적**: chef_id가 없는 레시피의 경우 빈 목록 반환

```python
@pytest.mark.asyncio
async def test_same_chef_no_chef(client: AsyncClient, recipe_without_chef):
    """요리사 없는 레시피의 같은 요리사 조회 테스트"""
    recipe_id = recipe_without_chef.id

    # When: 같은 요리사 레시피 조회
    response = await client.get(f"/api/v1/recipes/{recipe_id}/same-chef")

    # Then: 빈 목록 반환
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["has_more"] is False
```

### 3.4 시나리오 4: 페이지네이션

**목적**: 커서 기반 페이지네이션 동작 확인

```python
@pytest.mark.asyncio
async def test_similar_recipes_pagination(client: AsyncClient, many_similar_recipes):
    """유사 레시피 페이지네이션 테스트"""
    recipe_id = many_similar_recipes[0].id

    # Given: 첫 페이지 (5개)
    response1 = await client.get(f"/api/v1/recipes/{recipe_id}/similar?limit=5")
    assert response1.status_code == 200
    data1 = response1.json()

    # When: 다음 페이지
    assert data1["has_more"] is True
    cursor = data1["next_cursor"]
    response2 = await client.get(f"/api/v1/recipes/{recipe_id}/similar?limit=5&cursor={cursor}")

    # Then: 중복 없음
    assert response2.status_code == 200
    data2 = response2.json()
    ids1 = {item["id"] for item in data1["items"]}
    ids2 = {item["id"] for item in data2["items"]}
    assert ids1.isdisjoint(ids2)
```

### 3.5 시나리오 5: 잘못된 레시피 ID

**목적**: 존재하지 않는 레시피 ID로 요청 시 404 응답

```python
@pytest.mark.asyncio
async def test_similar_recipes_not_found(client: AsyncClient):
    """존재하지 않는 레시피 ID 테스트"""
    fake_id = "00000000-0000-0000-0000-000000000000"

    # When: 존재하지 않는 레시피 ID로 요청
    response = await client.get(f"/api/v1/recipes/{fake_id}/similar")

    # Then: 404 응답
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
```

---

## 4. 캐시 동작 검증

### 4.1 캐시 키 확인

```bash
# Redis CLI로 캐시 키 확인
docker exec -it naecipe-redis redis-cli

# 유사 레시피 캐시 키
keys recipes:*:similar

# 특정 레시피의 캐시 값
get recipes:550e8400-e29b-41d4-a716-446655440000:similar
```

### 4.2 캐시 TTL 확인

```bash
# TTL 확인 (초 단위)
ttl recipes:550e8400-e29b-41d4-a716-446655440000:similar
# 기대값: 600 (10분)
```

### 4.3 캐시 무효화 테스트

```python
@pytest.mark.asyncio
async def test_cache_invalidation_on_recipe_update(
    client: AsyncClient,
    sample_recipe,
    redis_client
):
    """레시피 수정 시 캐시 무효화 테스트"""
    recipe_id = sample_recipe.id

    # Given: 캐시 생성
    await client.get(f"/api/v1/recipes/{recipe_id}/similar")
    cache_key = f"recipes:{recipe_id}:similar"
    assert await redis_client.exists(cache_key)

    # When: 레시피 수정 (태그 변경)
    await client.patch(
        f"/api/v1/recipes/{recipe_id}",
        json={"tags": ["new-tag"]}
    )

    # Then: 캐시 무효화
    assert not await redis_client.exists(cache_key)
```

---

## 5. 성능 테스트

### 5.1 응답 시간 측정

```python
import time

@pytest.mark.asyncio
async def test_similar_recipes_performance(client: AsyncClient, sample_recipe):
    """유사 레시피 응답 시간 테스트"""
    recipe_id = sample_recipe.id

    # 캐시 미스 (첫 요청)
    start = time.time()
    response1 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
    cache_miss_time = (time.time() - start) * 1000  # ms

    # 캐시 히트 (두 번째 요청)
    start = time.time()
    response2 = await client.get(f"/api/v1/recipes/{recipe_id}/similar")
    cache_hit_time = (time.time() - start) * 1000  # ms

    # 성능 검증
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert cache_miss_time < 300  # 캐시 미스: < 300ms
    assert cache_hit_time < 50    # 캐시 히트: < 50ms
```

### 5.2 부하 테스트 (locust)

```python
# locustfile.py
from locust import HttpUser, task, between

class SimilarRecipesUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def get_similar(self):
        self.client.get("/api/v1/recipes/{recipe_id}/similar")

    @task(2)
    def get_same_chef(self):
        self.client.get("/api/v1/recipes/{recipe_id}/same-chef")

    @task(2)
    def get_related_tags(self):
        self.client.get("/api/v1/recipes/{recipe_id}/related-by-tags")

    @task(1)
    def get_category_popular(self):
        self.client.get("/api/v1/recipes/{recipe_id}/category-popular")
```

```bash
# 부하 테스트 실행
locust -f locustfile.py --host=http://localhost:8000
```

---

## 6. 디버깅 가이드

### 6.1 캐시 문제

```python
# Redis 연결 확인
from app.infra.redis import get_redis_cache

async def check_redis():
    cache = await get_redis_cache()
    await cache.set("test", "value")
    result = await cache.get("test")
    print(f"Redis OK: {result}")
```

### 6.2 유사도 계산 디버깅

```python
# 유사도 점수 로깅
import logging

logging.getLogger("app.recipes.services").setLevel(logging.DEBUG)
```

### 6.3 SQL 쿼리 확인

```python
# SQLAlchemy 쿼리 로깅
import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
```

---

## 7. 트러블슈팅

### 7.1 "Recipe not found" 에러

**원인**: 존재하지 않거나 비활성화된 레시피
**해결**:
```sql
SELECT id, is_active FROM recipes WHERE id = '{recipe_id}';
```

### 7.2 빈 유사 레시피 목록

**원인**: 태그/재료가 없는 레시피
**해결**:
```sql
-- 태그 확인
SELECT * FROM recipe_tags WHERE recipe_id = '{recipe_id}';

-- 재료 확인
SELECT * FROM recipe_ingredients WHERE recipe_id = '{recipe_id}';
```

### 7.3 캐시가 작동하지 않음

**원인**: Redis 연결 문제
**해결**:
```bash
# Redis 상태 확인
docker exec -it naecipe-redis redis-cli ping
# 기대 응답: PONG
```

---

## 8. 다음 단계

1. **구현 시작**: `/speckit.tasks` 실행으로 태스크 생성
2. **라우터 구현**: `app/recipes/router.py`에 엔드포인트 추가
3. **서비스 구현**: `SimilarRecipeService` 클래스 생성
4. **테스트 작성**: `tests/recipes/test_similar_recipes.py`
5. **캐시 통합**: Redis 캐싱 로직 구현
