# Quickstart: 레시피북 기본 CRUD

**Feature Branch**: `007-cookbook-basic-crud`
**Created**: 2025-12-11

## 통합 시나리오

### 시나리오 1: 첫 사용자의 레시피북 자동 생성

```bash
# 1. 로그인 (JWT 토큰 획득)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}' \
  | jq -r '.access_token')

# 2. 레시피북 목록 조회 (첫 조회 시 "내 레시피북" 자동 생성)
curl -X GET http://localhost:8000/api/v1/cookbooks \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 예상 응답:
# {
#   "items": [
#     {
#       "id": "...",
#       "name": "내 레시피북",
#       "description": null,
#       "cover_image_url": null,
#       "sort_order": 0,
#       "is_default": true,
#       "saved_recipe_count": 0,
#       "created_at": "2025-12-11T...",
#       "updated_at": "2025-12-11T..."
#     }
#   ],
#   "total": 1
# }
```

### 시나리오 2: 새 레시피북 생성

```bash
# 레시피북 생성
COOKBOOK_ID=$(curl -s -X POST http://localhost:8000/api/v1/cookbooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "한식 모음",
    "description": "한식 레시피 모음집",
    "cover_image_url": "https://example.com/korean-food.jpg"
  }' | jq -r '.id')

echo "Created cookbook: $COOKBOOK_ID"

# 예상 응답:
# {
#   "id": "...",
#   "name": "한식 모음",
#   "description": "한식 레시피 모음집",
#   "cover_image_url": "https://example.com/korean-food.jpg",
#   "sort_order": 1,
#   "is_default": false,
#   "saved_recipe_count": 0,
#   "created_at": "...",
#   "updated_at": "..."
# }
```

### 시나리오 3: 레시피북 수정

```bash
# 레시피북 수정
curl -X PUT "http://localhost:8000/api/v1/cookbooks/$COOKBOOK_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "맛있는 한식",
    "description": "집에서 만드는 한식 레시피"
  }' | jq

# 예상 응답: 수정된 레시피북 정보
```

### 시나리오 4: 레시피북 순서 변경

```bash
# 현재 목록 조회
curl -X GET http://localhost:8000/api/v1/cookbooks \
  -H "Authorization: Bearer $TOKEN" | jq '.items[].id'

# 순서 변경 (두 번째를 첫 번째로)
curl -X PATCH http://localhost:8000/api/v1/cookbooks/reorder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cookbook_ids": [
      "'"$COOKBOOK_ID"'",
      "<default_cookbook_id>"
    ]
  }' | jq
```

### 시나리오 5: 레시피북 삭제

```bash
# 일반 레시피북 삭제 (성공)
curl -X DELETE "http://localhost:8000/api/v1/cookbooks/$COOKBOOK_ID" \
  -H "Authorization: Bearer $TOKEN" -v

# HTTP 204 No Content

# 기본 레시피북 삭제 시도 (실패)
curl -X DELETE "http://localhost:8000/api/v1/cookbooks/<default_cookbook_id>" \
  -H "Authorization: Bearer $TOKEN"

# 예상 응답:
# {
#   "detail": "기본 레시피북은 삭제할 수 없습니다",
#   "code": "CANNOT_DELETE_DEFAULT_COOKBOOK"
# }
```

## 검증 체크리스트

### 기능 검증

- [ ] 첫 레시피북 조회 시 "내 레시피북" 자동 생성
- [ ] 레시피북 생성 (이름 필수, 설명/이미지 선택)
- [ ] 레시피북 목록 조회 (sort_order 순)
- [ ] 레시피북 상세 조회
- [ ] 레시피북 수정
- [ ] 레시피북 삭제 (기본 레시피북 제외)
- [ ] 레시피북 순서 변경

### 권한 검증

- [ ] 미인증 사용자 접근 거부 (401)
- [ ] 타인 레시피북 접근 거부 (404)
- [ ] 기본 레시피북 삭제 거부 (400)

### 데이터 검증

- [ ] 이름 1-100자 제한
- [ ] 설명 500자 제한
- [ ] URL 형식 검증
- [ ] 앞뒤 공백 제거 (trim)

## 테스트 명령어

```bash
# 테스트 실행
pytest tests/cookbooks/ -v

# 특정 테스트만 실행
pytest tests/cookbooks/test_cookbook_crud.py -v

# 커버리지 포함
pytest tests/cookbooks/ --cov=app/cookbooks --cov-report=term-missing
```
