# Research: 사용자 프로필 및 취향 설정

**Feature**: 003-user-profile-preferences
**Date**: 2025-12-10

## 1. 기존 시스템 분석

### 1.1 User 모델 현황

**파일**: `services/user-service/src/user_service/models/user.py`

현재 User 모델은 인증 목적으로 설계되어 다음 필드만 포함:
- `id` (UUID): Primary Key
- `email` (String): Unique, 로그인 ID
- `password_hash` (String): 비밀번호 해시
- `status` (Enum): ACTIVE, INACTIVE, LOCKED
- `created_at`, `updated_at`, `locked_until`: 타임스탬프

**결론**: 프로필 정보(이름, 이미지, 식이제한, 알레르기 등)는 별도 테이블로 분리해야 함.

### 1.2 기존 Relationship

- `User` ↔ `OAuthAccount`: 1:N (이미 구현됨)
- `User` ↔ `UserProfile`: 1:1 (신규)
- `User` ↔ `TastePreference`: 1:N (신규)

## 2. 기술 결정

### 2.1 프로필 저장 전략

**Decision**: UserProfile 별도 테이블 (1:1 관계)

**Rationale**:
- User 테이블은 인증 목적으로 유지 (SRP 원칙)
- 프로필 데이터는 자주 변경되지만, 인증 데이터는 드물게 변경
- 향후 프로필 확장 시 User 테이블 스키마 변경 불필요

**Alternatives Considered**:
1. ❌ User 테이블 확장: 기존 인증 로직에 영향, 마이그레이션 리스크
2. ❌ JSONB 단일 컬럼: 쿼리/인덱싱 어려움, 스키마 검증 불가

### 2.2 맛 취향 저장 전략

**Decision**: TastePreference 테이블 (1:N 관계, category 기반)

**Rationale**:
- `overall` + 카테고리별(korean, japanese 등) 취향 별도 저장
- 카테고리 추가 시 스키마 변경 불필요
- AI Service에서 카테고리별 쿼리 용이

**Structure**:
```
user_id | category | sweetness | saltiness | spiciness | sourness
--------|----------|-----------|-----------|-----------|----------
uuid1   | overall  | 3         | 3         | 4         | 2
uuid1   | korean   | 3         | 4         | 5         | 2
```

**Alternatives Considered**:
1. ❌ JSONB 단일 컬럼: 카테고리별 쿼리 복잡, 인덱싱 어려움
2. ❌ 카테고리별 컬럼 (sweetness_korean 등): 카테고리 추가 시 스키마 변경 필요

### 2.3 Predefined Values 관리

**Decision**: Python Enum + 데이터베이스 CHECK 제약

**Rationale**:
- 컴파일 타임 검증 (IDE 자동완성)
- 런타임 Pydantic 검증
- 데이터베이스 레벨 무결성 보장

**Implementation**:
```python
# schemas/preference.py
class DietaryRestriction(str, Enum):
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    # ...

# models/user_profile.py
dietary_restrictions = Column(ARRAY(String), nullable=True)
# CHECK constraint in migration: array elements must be in predefined list
```

### 2.4 API 설계 패턴

**Decision**: 부분 업데이트(PATCH 의미론) + PUT 엔드포인트

**Rationale**:
- `PUT /users/me/preferences`는 전체 교체가 아닌 제공된 필드만 업데이트
- 클라이언트가 변경하려는 필드만 전송 가능
- 누락된 필드는 기존 값 유지

**Example**:
```json
// 요청: 알레르기만 업데이트
PUT /users/me/preferences
{
  "allergies": ["peanut", "shellfish"]
}
// 결과: 다른 필드(dietaryRestrictions, tastePreferences 등)는 유지
```

### 2.5 이벤트 발행 전략

**Decision**: UserPreferenceUpdated 이벤트 (Kafka)

**Rationale**:
- AI Agent Service에서 사용자 취향 변경 시 캐시 무효화 필요
- Analytics Service에서 취향 변경 추적 필요
- 비동기 처리로 API 응답 시간에 영향 없음

**Event Schema**:
```json
{
  "eventType": "UserPreferenceUpdated",
  "version": "1.0",
  "timestamp": "2025-12-10T10:00:00Z",
  "payload": {
    "userId": "uuid",
    "changedFields": ["allergies", "tastePreferences.korean"],
    "preferences": {
      "allergies": ["peanut", "shellfish"],
      "tastePreferences": {
        "korean": {"spiciness": 5}
      }
    }
  }
}
```

## 3. 성능 최적화

### 3.1 프로필 조회 최적화

**Strategy**: Eager Loading + Redis 캐시

**Implementation**:
1. SQLAlchemy `selectinload`로 User + UserProfile + TastePreferences 한 번에 로드
2. Redis에 직렬화된 프로필 캐시 (TTL: 5분)
3. 프로필 변경 시 캐시 무효화

**Expected Performance**: 조회 < 50ms (캐시 히트), < 100ms (캐시 미스)

### 3.2 동시성 처리

**Strategy**: Last-Write-Wins (LWW)

**Rationale**:
- 프로필 수정은 사용자 본인만 가능 (다중 기기 충돌 가능)
- 복잡한 충돌 해결보다 최신 값 우선이 사용자 경험에 적합
- `updated_at` 타임스탬프로 변경 추적

## 4. 보안 고려사항

### 4.1 입력 검증

| 필드 | 검증 규칙 |
|------|----------|
| display_name | 1-50자, 공백 trim |
| profile_image_url | URL 형식 (http/https), 최대 2048자 |
| dietary_restrictions | Enum 값 목록 |
| allergies | Enum 값 목록 |
| taste_* | 1-5 정수 범위 |
| skill_level | 1-5 정수 범위 |
| household_size | 1-20 정수 범위 |
| cuisine_preferences | Enum 값 목록, 최대 10개 |

### 4.2 인가 규칙

- 모든 API는 JWT 인증 필수
- 사용자는 자신의 프로필만 조회/수정 가능
- `user_id`는 JWT에서 추출 (경로 파라미터 불필요)

## 5. 테스트 전략

### 5.1 Contract 테스트

- Schemathesis로 OpenAPI 스펙 기반 자동 테스트
- 모든 요청/응답 스키마 검증

### 5.2 Integration 테스트

| 시나리오 | 검증 항목 |
|---------|----------|
| 프로필 조회 | 신규 사용자 기본값, 기존 사용자 전체 필드 |
| 프로필 수정 | 부분 업데이트, 전체 업데이트, 유효성 오류 |
| 취향 설정 | overall/카테고리별, 범위 초과, 잘못된 Enum |
| 동시 수정 | LWW 동작 확인 |
| 캐시 | 히트/미스, 무효화 |

## 6. 의존성

### 6.1 기존 코드 재사용

| 컴포넌트 | 출처 | 용도 |
|---------|-----|------|
| `get_current_user` | SPEC-001 deps.py | JWT 인증 의존성 |
| `get_db` | SPEC-001 deps.py | DB 세션 의존성 |
| `get_redis` | SPEC-001 deps.py | Redis 클라이언트 |
| logging/tracing | SPEC-001 core/ | 관측성 |

### 6.2 신규 의존성

- 없음 (기존 스택으로 충분)

## 7. 마이그레이션 계획

### 7.1 데이터베이스 마이그레이션

1. `user_profiles` 테이블 생성
2. `taste_preferences` 테이블 생성
3. 기존 사용자에 대해 기본 UserProfile 레코드 생성 (display_name = email 앞부분)

### 7.2 호환성

- 기존 User 모델 변경 없음 (relationship 추가만)
- 기존 인증 API 영향 없음
- 신규 API만 추가
