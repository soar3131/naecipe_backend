# Quickstart: 사용자 프로필 및 취향 설정

**Feature**: 003-user-profile-preferences
**Date**: 2025-12-10

## 개요

이 문서는 사용자 프로필 및 취향 설정 API의 통합 시나리오를 설명합니다.

## 사전 요구사항

1. User Service 실행 중 (`localhost:8002`)
2. PostgreSQL, Redis 실행 중
3. 사용자 계정 생성 완료 (SPEC-001)
4. JWT 토큰 발급 완료

## 시나리오 1: 신규 사용자 프로필 설정

### Step 1: 로그인 후 프로필 조회

```bash
# JWT 토큰 발급 (SPEC-001)
TOKEN=$(curl -s -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Password123!"}' \
  | jq -r '.data.accessToken')

# 프로필 조회
curl -X GET http://localhost:8002/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  | jq
```

**응답 (신규 사용자)**:
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "displayName": "",
    "profileImageUrl": null,
    "createdAt": "2025-12-10T10:00:00Z",
    "updatedAt": "2025-12-10T10:00:00Z"
  }
}
```

### Step 2: 기본 프로필 수정

```bash
curl -X PUT http://localhost:8002/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "홍길동",
    "profileImageUrl": "https://cdn.naecipe.com/profiles/user123.jpg"
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "displayName": "홍길동",
    "profileImageUrl": "https://cdn.naecipe.com/profiles/user123.jpg",
    "createdAt": "2025-12-10T10:00:00Z",
    "updatedAt": "2025-12-10T10:05:00Z"
  }
}
```

### Step 3: 알레르기 및 식이 제한 설정

```bash
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dietaryRestrictions": ["vegetarian"],
    "allergies": ["peanut", "shellfish"]
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "dietaryRestrictions": ["vegetarian"],
    "allergies": ["peanut", "shellfish"],
    "cuisinePreferences": [],
    "skillLevel": null,
    "householdSize": null,
    "tastePreferences": {},
    "updatedAt": "2025-12-10T10:10:00Z"
  }
}
```

### Step 4: 맛 취향 설정

```bash
# 전체(overall) 취향 설정
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tastePreferences": {
      "overall": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      }
    }
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "dietaryRestrictions": ["vegetarian"],
    "allergies": ["peanut", "shellfish"],
    "cuisinePreferences": [],
    "skillLevel": null,
    "householdSize": null,
    "tastePreferences": {
      "overall": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      }
    },
    "updatedAt": "2025-12-10T10:15:00Z"
  }
}
```

### Step 5: 카테고리별 취향 추가

```bash
# 한식은 더 매운 것을 선호
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tastePreferences": {
      "korean": {
        "spiciness": 5
      }
    }
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "dietaryRestrictions": ["vegetarian"],
    "allergies": ["peanut", "shellfish"],
    "cuisinePreferences": [],
    "skillLevel": null,
    "householdSize": null,
    "tastePreferences": {
      "overall": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      },
      "korean": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 5,
        "sourness": 2
      }
    },
    "updatedAt": "2025-12-10T10:20:00Z"
  }
}
```

> **Note**: 카테고리별 취향에서 제공하지 않은 값(sweetness, saltiness, sourness)은 overall 값을 상속받습니다.

## 시나리오 2: 취향 옵션 조회

### 식이 제한 옵션 조회

```bash
curl -X GET http://localhost:8002/api/v1/users/me/preferences/dietary-options \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": [
    {"value": "vegetarian", "label": "채식 (유제품/계란 허용)"},
    {"value": "vegan", "label": "비건 (동물성 제품 불가)"},
    {"value": "pescatarian", "label": "페스코 (해산물 허용)"},
    {"value": "halal", "label": "할랄"},
    {"value": "kosher", "label": "코셔"},
    {"value": "gluten_free", "label": "글루텐 프리"},
    {"value": "lactose_free", "label": "유당 불내증"},
    {"value": "low_sodium", "label": "저염식"},
    {"value": "low_sugar", "label": "저당식"}
  ]
}
```

### 알레르기 옵션 조회

```bash
curl -X GET http://localhost:8002/api/v1/users/me/preferences/allergy-options \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": [
    {"value": "peanut", "label": "땅콩"},
    {"value": "tree_nut", "label": "견과류"},
    {"value": "milk", "label": "우유"},
    {"value": "egg", "label": "달걀"},
    {"value": "wheat", "label": "밀"},
    {"value": "soy", "label": "대두"},
    {"value": "fish", "label": "생선"},
    {"value": "shellfish", "label": "갑각류/조개류"},
    {"value": "sesame", "label": "참깨"}
  ]
}
```

## 시나리오 3: 유효성 검사 오류

### 잘못된 식이 제한 값

```bash
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dietaryRestrictions": ["invalid_diet"]
  }' \
  | jq
```

**응답 (400 Bad Request)**:
```json
{
  "success": false,
  "error": {
    "type": "/errors/validation",
    "title": "Validation Error",
    "status": 400,
    "detail": "입력값이 올바르지 않습니다.",
    "instance": "/api/v1/users/me/preferences",
    "errors": [
      {
        "field": "dietaryRestrictions.0",
        "message": "허용되지 않는 식이 제한 값입니다: invalid_diet",
        "code": "INVALID_ENUM"
      }
    ]
  }
}
```

### 맛 취향 범위 초과

```bash
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tastePreferences": {
      "overall": {
        "spiciness": 10
      }
    }
  }' \
  | jq
```

**응답 (400 Bad Request)**:
```json
{
  "success": false,
  "error": {
    "type": "/errors/validation",
    "title": "Validation Error",
    "status": 400,
    "detail": "입력값이 올바르지 않습니다.",
    "instance": "/api/v1/users/me/preferences",
    "errors": [
      {
        "field": "tastePreferences.overall.spiciness",
        "message": "매운맛 선호도는 1-5 사이여야 합니다",
        "code": "VALUE_OUT_OF_RANGE"
      }
    ]
  }
}
```

### 표시 이름 길이 초과

```bash
curl -X PUT http://localhost:8002/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "이름이너무길어서오십자를초과하는경우에는유효성검사오류가발생합니다이름이너무길어요"
  }' \
  | jq
```

**응답 (400 Bad Request)**:
```json
{
  "success": false,
  "error": {
    "type": "/errors/validation",
    "title": "Validation Error",
    "status": 400,
    "detail": "입력값이 올바르지 않습니다.",
    "instance": "/api/v1/users/me",
    "errors": [
      {
        "field": "displayName",
        "message": "표시 이름은 1-50자 사이여야 합니다",
        "code": "STRING_LENGTH"
      }
    ]
  }
}
```

## 시나리오 4: 인증 오류

### 토큰 없이 요청

```bash
curl -X GET http://localhost:8002/api/v1/users/me \
  | jq
```

**응답 (401 Unauthorized)**:
```json
{
  "success": false,
  "error": {
    "type": "/errors/unauthorized",
    "title": "Unauthorized",
    "status": 401,
    "detail": "인증 토큰이 필요합니다."
  }
}
```

### 만료된 토큰

```bash
curl -X GET http://localhost:8002/api/v1/users/me \
  -H "Authorization: Bearer expired_token_here" \
  | jq
```

**응답 (401 Unauthorized)**:
```json
{
  "success": false,
  "error": {
    "type": "/errors/unauthorized",
    "title": "Unauthorized",
    "status": 401,
    "detail": "인증 토큰이 만료되었습니다."
  }
}
```

## 시나리오 5: 알레르기 설정 초기화

빈 배열을 전송하여 기존 설정을 제거할 수 있습니다.

```bash
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "allergies": []
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "dietaryRestrictions": ["vegetarian"],
    "allergies": [],
    "cuisinePreferences": [],
    "skillLevel": null,
    "householdSize": null,
    "tastePreferences": {
      "overall": {...},
      "korean": {...}
    },
    "updatedAt": "2025-12-10T10:30:00Z"
  }
}
```

## 시나리오 6: 전체 취향 설정 (한 번에)

```bash
curl -X PUT http://localhost:8002/api/v1/users/me/preferences \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dietaryRestrictions": ["vegetarian", "gluten_free"],
    "allergies": ["peanut", "shellfish", "milk"],
    "cuisinePreferences": ["korean", "japanese", "italian"],
    "skillLevel": 3,
    "householdSize": 2,
    "tastePreferences": {
      "overall": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      },
      "korean": {
        "spiciness": 5
      },
      "japanese": {
        "sweetness": 4
      }
    }
  }' \
  | jq
```

**응답**:
```json
{
  "success": true,
  "data": {
    "dietaryRestrictions": ["vegetarian", "gluten_free"],
    "allergies": ["peanut", "shellfish", "milk"],
    "cuisinePreferences": ["korean", "japanese", "italian"],
    "skillLevel": 3,
    "householdSize": 2,
    "tastePreferences": {
      "overall": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      },
      "korean": {
        "sweetness": 3,
        "saltiness": 3,
        "spiciness": 5,
        "sourness": 2
      },
      "japanese": {
        "sweetness": 4,
        "saltiness": 3,
        "spiciness": 4,
        "sourness": 2
      }
    },
    "updatedAt": "2025-12-10T10:35:00Z"
  }
}
```

## 테스트 데이터 설정

### 테스트용 사용자 생성 및 설정

```bash
#!/bin/bash

BASE_URL="http://localhost:8002/api/v1"

# 1. 테스트 사용자 생성
curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# 2. 로그인 및 토큰 획득
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPassword123!"}' \
  | jq -r '.data.accessToken')

# 3. 프로필 설정
curl -s -X PUT "$BASE_URL/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"displayName": "테스트 사용자"}'

# 4. 취향 설정
curl -s -X PUT "$BASE_URL/users/me/preferences" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "allergies": ["peanut"],
    "tastePreferences": {
      "overall": {"sweetness": 3, "saltiness": 3, "spiciness": 3, "sourness": 3}
    }
  }'

echo "Test user created and configured!"
echo "Token: $TOKEN"
```

## 관련 문서

- [spec.md](./spec.md) - 기능 명세
- [data-model.md](./data-model.md) - 데이터 모델
- [contracts/openapi.yaml](./contracts/openapi.yaml) - API 명세
- [research.md](./research.md) - 기술 결정 근거
