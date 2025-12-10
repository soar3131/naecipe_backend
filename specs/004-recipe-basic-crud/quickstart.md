# Quickstart: 원본 레시피 기본 CRUD

**Branch**: `004-recipe-basic-crud` | **Date**: 2025-12-10

## Overview

Recipe Service(8001) API를 활용한 통합 시나리오를 설명한다.

---

## Prerequisites

### 1. 서비스 실행

```bash
# Docker Compose로 인프라 실행
docker-compose up -d postgres redis

# Recipe Service 실행
cd services/recipe-service
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. 테스트 데이터 준비

```bash
# 마이그레이션 실행
cd services/recipe-service
alembic upgrade head

# 시드 데이터 삽입 (선택사항)
python scripts/seed_test_data.py
```

---

## Scenario 1: 레시피 목록 탐색

### Step 1: 레시피 목록 조회

```bash
curl -X GET "http://localhost:8001/api/v1/recipes?limit=20" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "김치찌개",
      "thumbnail_url": "https://example.com/kimchi-jjigae.jpg",
      "cooking_time_minutes": 30,
      "difficulty": "medium",
      "avg_rating": 4.5,
      "chef_name": "백종원"
    },
    // ... 19개 더
  ],
  "next_cursor": "eyJzY29yZSI6MTAwLCJpZCI6InV1aWQifQ==",
  "has_more": true
}
```

### Step 2: 다음 페이지 로드 (무한 스크롤)

```bash
curl -X GET "http://localhost:8001/api/v1/recipes?cursor=eyJzY29yZSI6MTAwLCJpZCI6InV1aWQifQ==&limit=20" \
  -H "Accept: application/json"
```

---

## Scenario 2: 레시피 상세 조회

### Step 1: 레시피 상세 정보 요청

```bash
curl -X GET "http://localhost:8001/api/v1/recipes/550e8400-e29b-41d4-a716-446655440001" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "김치찌개",
  "description": "돼지고기와 김치로 만드는 깊은 맛의 찌개",
  "cooking_time_minutes": 30,
  "servings": 2,
  "difficulty": "medium",
  "thumbnail_url": "https://example.com/kimchi-jjigae.jpg",
  "video_url": "https://youtube.com/watch?v=...",
  "avg_rating": 4.5,
  "view_count": 15000,
  "save_count": 2300,
  "ingredients": [
    {
      "name": "돼지고기",
      "amount": "200",
      "unit": "g",
      "order_index": 1,
      "is_optional": false,
      "substitutes": null
    },
    {
      "name": "김치",
      "amount": "300",
      "unit": "g",
      "order_index": 2,
      "is_optional": false,
      "substitutes": null
    }
    // ...
  ],
  "steps": [
    {
      "step_number": 1,
      "instruction": "돼지고기를 한입 크기로 썰어주세요",
      "duration_seconds": 120,
      "tips": "기름기가 있는 부위가 더 맛있어요",
      "image_url": null
    },
    {
      "step_number": 2,
      "instruction": "냄비에 참기름을 두르고 돼지고기를 볶아주세요",
      "duration_seconds": 180,
      "tips": "센 불에서 빠르게 볶아주세요",
      "image_url": null
    }
    // ...
  ],
  "tags": [
    {"name": "한식", "category": "cuisine"},
    {"name": "찌개", "category": "dish_type"},
    {"name": "점심", "category": "meal_type"}
  ],
  "chef": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "백종원",
    "profile_image_url": "https://example.com/baek.jpg",
    "specialty": "한식"
  }
}
```

---

## Scenario 3: 인기 레시피 조회

### Step 1: 전체 인기 레시피

```bash
curl -X GET "http://localhost:8001/api/v1/recipes/popular?limit=10" \
  -H "Accept: application/json"
```

### Step 2: 카테고리별 인기 레시피

```bash
curl -X GET "http://localhost:8001/api/v1/recipes/popular?category=한식&limit=10" \
  -H "Accept: application/json"
```

---

## Scenario 4: 요리사 탐색

### Step 1: 요리사 목록 조회

```bash
curl -X GET "http://localhost:8001/api/v1/chefs?limit=20" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "items": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "백종원",
      "profile_image_url": "https://example.com/baek.jpg",
      "specialty": "한식",
      "recipe_count": 150,
      "is_verified": true
    }
    // ...
  ],
  "next_cursor": "...",
  "has_more": true
}
```

### Step 2: 요리사 상세 조회

```bash
curl -X GET "http://localhost:8001/api/v1/chefs/660e8400-e29b-41d4-a716-446655440001" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "백종원",
  "profile_image_url": "https://example.com/baek.jpg",
  "bio": "대한민국 대표 요리 연구가",
  "specialty": "한식",
  "recipe_count": 150,
  "total_views": 50000000,
  "avg_rating": 4.8,
  "is_verified": true,
  "platforms": [
    {
      "platform": "youtube",
      "platform_url": "https://youtube.com/@paikilog",
      "subscriber_count": 5000000
    },
    {
      "platform": "instagram",
      "platform_url": "https://instagram.com/paikjongwon",
      "subscriber_count": 2000000
    }
  ]
}
```

### Step 3: 인기 요리사 조회

```bash
curl -X GET "http://localhost:8001/api/v1/chefs/popular?limit=5" \
  -H "Accept: application/json"
```

---

## Scenario 5: 요리사별 레시피 조회

### Step 1: 특정 요리사의 레시피 목록

```bash
curl -X GET "http://localhost:8001/api/v1/chefs/660e8400-e29b-41d4-a716-446655440001/recipes?limit=20" \
  -H "Accept: application/json"
```

**Response**:
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "김치찌개",
      "thumbnail_url": "https://example.com/kimchi-jjigae.jpg",
      "cooking_time_minutes": 30,
      "difficulty": "medium",
      "avg_rating": 4.5,
      "chef_name": "백종원"
    }
    // ... 해당 요리사의 레시피만
  ],
  "next_cursor": "...",
  "has_more": true
}
```

---

## Error Handling

### 404 Not Found

```bash
curl -X GET "http://localhost:8001/api/v1/recipes/nonexistent-id" \
  -H "Accept: application/json"
```

**Response** (404):
```json
{
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "레시피를 찾을 수 없습니다",
    "details": {
      "recipe_id": "nonexistent-id"
    }
  }
}
```

### 400 Bad Request (잘못된 커서)

```bash
curl -X GET "http://localhost:8001/api/v1/recipes?cursor=invalid-cursor" \
  -H "Accept: application/json"
```

**Response** (400):
```json
{
  "error": {
    "code": "INVALID_CURSOR",
    "message": "잘못된 커서 형식입니다",
    "details": {
      "cursor": "invalid-cursor"
    }
  }
}
```

---

## Performance Tips

### 1. 캐시 활용

레시피 상세와 요리사 상세는 1시간 캐싱되므로 반복 요청 시 빠른 응답.

### 2. 필요한 데이터만 요청

목록 조회 시 상세 정보(재료, 단계)는 포함되지 않음. 상세가 필요하면 별도 요청.

### 3. 커서 페이지네이션

다음 페이지 요청 시 반드시 `next_cursor` 값을 사용. OFFSET 방식보다 안정적.

---

## Testing

### 단위 테스트 실행

```bash
cd services/recipe-service
pytest tests/unit/ -v
```

### 통합 테스트 실행

```bash
cd services/recipe-service
pytest tests/integration/ -v --db-url="postgresql://..."
```

### API 계약 테스트

```bash
cd services/recipe-service
pytest tests/contract/ -v
```
