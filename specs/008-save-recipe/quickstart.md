# Quickstart: 레시피 저장

**Feature Branch**: `008-save-recipe`
**Date**: 2025-12-11

## Prerequisites

- 사용자 인증 토큰 (JWT)
- 레시피북 생성 완료 (SPEC-007)
- 원본 레시피 존재 (SPEC-004)

## Integration Scenarios

### Scenario 1: 레시피 검색 → 저장 (Core Loop)

**사용자 스토리**: 사용자가 레시피를 검색하고 마음에 드는 레시피를 레시피북에 저장한다.

```bash
# 1. 레시피 검색
GET /api/v1/recipes?q=김치찌개
# Response: { "items": [{ "id": "recipe-uuid-1", "title": "백종원 김치찌개", ... }] }

# 2. 기본 레시피북 확인 (또는 특정 레시피북 선택)
GET /api/v1/cookbooks
# Response: { "items": [{ "id": "cookbook-uuid-1", "name": "내 레시피북", "is_default": true }] }

# 3. 레시피 저장
POST /api/v1/cookbooks/cookbook-uuid-1/recipes
Authorization: Bearer <token>
Content-Type: application/json

{
  "recipe_id": "recipe-uuid-1",
  "memo": "백종원 레시피! 돼지고기 300g 필요"
}

# Response: 201 Created
{
  "id": "saved-recipe-uuid-1",
  "cookbook_id": "cookbook-uuid-1",
  "recipe": {
    "id": "recipe-uuid-1",
    "title": "백종원 김치찌개",
    "thumbnail_url": "https://..."
  },
  "memo": "백종원 레시피! 돼지고기 300g 필요",
  "cook_count": 0,
  "created_at": "2025-12-11T10:00:00Z"
}
```

### Scenario 2: 저장된 레시피 목록 조회

**사용자 스토리**: 사용자가 레시피북에서 저장한 레시피를 확인한다.

```bash
# 저장된 레시피 목록 조회
GET /api/v1/cookbooks/cookbook-uuid-1/recipes?limit=20&offset=0
Authorization: Bearer <token>

# Response: 200 OK
{
  "items": [
    {
      "id": "saved-recipe-uuid-1",
      "cookbook_id": "cookbook-uuid-1",
      "recipe": {
        "id": "recipe-uuid-1",
        "title": "백종원 김치찌개",
        "thumbnail_url": "https://...",
        "chef_name": "백종원"
      },
      "memo": "백종원 레시피! 돼지고기 300g 필요",
      "cook_count": 0,
      "created_at": "2025-12-11T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Scenario 3: 저장된 레시피 상세 조회

**사용자 스토리**: 사용자가 저장한 레시피의 상세 정보를 확인한다.

```bash
# 상세 조회
GET /api/v1/cookbooks/cookbook-uuid-1/recipes/saved-recipe-uuid-1
Authorization: Bearer <token>

# Response: 200 OK
{
  "id": "saved-recipe-uuid-1",
  "cookbook_id": "cookbook-uuid-1",
  "recipe": {
    "id": "recipe-uuid-1",
    "title": "백종원 김치찌개",
    "description": "집에서 간단하게 만드는 김치찌개",
    "thumbnail_url": "https://...",
    "video_url": "https://youtube.com/...",
    "chef_name": "백종원",
    "prep_time_minutes": 10,
    "cook_time_minutes": 20,
    "servings": 2,
    "difficulty": "easy",
    "ingredients": [
      { "name": "김치", "amount": "200", "unit": "g" },
      { "name": "돼지고기", "amount": "150", "unit": "g" },
      { "name": "두부", "amount": "1/2", "unit": "모" }
    ],
    "steps": [
      { "step_number": 1, "description": "김치를 먹기 좋게 썰어준다" },
      { "step_number": 2, "description": "돼지고기를 볶아준다" }
    ],
    "tags": ["한식", "찌개", "간단요리"]
  },
  "memo": "백종원 레시피! 돼지고기 300g 필요",
  "cook_count": 0,
  "personal_rating": null,
  "last_cooked_at": null,
  "created_at": "2025-12-11T10:00:00Z"
}
```

### Scenario 4: 메모 수정

**사용자 스토리**: 사용자가 저장한 레시피의 메모를 수정한다.

```bash
PUT /api/v1/cookbooks/cookbook-uuid-1/recipes/saved-recipe-uuid-1
Authorization: Bearer <token>
Content-Type: application/json

{
  "memo": "2인분 기준, 매운맛 원하면 청양고추 추가"
}

# Response: 200 OK
{
  "id": "saved-recipe-uuid-1",
  "memo": "2인분 기준, 매운맛 원하면 청양고추 추가",
  ...
}
```

### Scenario 5: 저장된 레시피 삭제

**사용자 스토리**: 사용자가 저장한 레시피를 삭제한다.

```bash
DELETE /api/v1/cookbooks/cookbook-uuid-1/recipes/saved-recipe-uuid-1
Authorization: Bearer <token>

# Response: 204 No Content
```

## Error Scenarios

### 중복 저장 시도 (409 Conflict)

```bash
# 동일 레시피를 같은 레시피북에 다시 저장
POST /api/v1/cookbooks/cookbook-uuid-1/recipes
{
  "recipe_id": "recipe-uuid-1"  # 이미 저장된 레시피
}

# Response: 409 Conflict
{
  "detail": "Recipe already saved to this cookbook",
  "code": "RECIPE_ALREADY_SAVED"
}
```

### 존재하지 않는 레시피 (404 Not Found)

```bash
POST /api/v1/cookbooks/cookbook-uuid-1/recipes
{
  "recipe_id": "non-existent-uuid"
}

# Response: 404 Not Found
{
  "detail": "Recipe not found",
  "code": "RECIPE_NOT_FOUND"
}
```

### 다른 사용자의 레시피북 접근 (404 Not Found)

```bash
# 다른 사용자의 레시피북에 접근 (권한 없음 마스킹)
GET /api/v1/cookbooks/other-user-cookbook-uuid/recipes
Authorization: Bearer <my-token>

# Response: 404 Not Found
{
  "detail": "Cookbook not found",
  "code": "COOKBOOK_NOT_FOUND"
}
```

### 메모 길이 초과 (422 Validation Error)

```bash
PUT /api/v1/cookbooks/cookbook-uuid-1/recipes/saved-recipe-uuid-1
{
  "memo": "[1001자 이상의 긴 텍스트]"
}

# Response: 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "memo"],
      "msg": "ensure this value has at most 1000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

## Test Commands

```bash
# 전체 테스트 실행
pytest tests/cookbooks/test_saved_recipe*.py -v

# 통합 테스트만
pytest tests/cookbooks/test_saved_recipe_crud.py -v

# 서비스 단위 테스트만
pytest tests/cookbooks/test_saved_recipe_service.py -v

# 커버리지 포함
pytest tests/cookbooks/test_saved_recipe*.py --cov=app/cookbooks --cov-report=term-missing
```

## Future Extensions

### SPEC-009: AI 레시피 보정
- 저장된 레시피에 대해 AI 보정 요청
- RecipeVariation 생성 및 active_version_id 설정

### SPEC-010: 조리 피드백
- 조리 완료 기록 (cook_count 증가)
- 개인 평점 설정 (personal_rating)
- 마지막 조리 일시 기록 (last_cooked_at)
