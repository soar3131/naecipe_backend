# Tasks: 사용자 프로필 및 취향 설정

**Input**: Design documents from `/specs/003-user-profile-preferences/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Service Root**: `services/user-service/src/user_service/`
- **Tests Root**: `services/user-service/tests/`
- Paths shown below are relative to `services/user-service/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 프로필/취향 기능을 위한 기본 구조 설정

- [x] T001 [P] Enum 정의 생성 - `src/user_service/schemas/enums.py` (DietaryRestriction, Allergy, CuisineCategory)
- [x] T002 [P] 프로필 Pydantic 스키마 생성 - `src/user_service/schemas/profile.py`
- [x] T003 [P] 취향 Pydantic 스키마 생성 - `src/user_service/schemas/preference.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 의존하는 핵심 인프라

**⚠️ CRITICAL**: 이 단계가 완료되어야 User Story 구현 시작 가능

- [x] T004 UserProfile SQLAlchemy 모델 생성 - `src/user_service/models/user_profile.py`
- [x] T005 TastePreference SQLAlchemy 모델 생성 - `src/user_service/models/taste_preference.py`
- [x] T006 User 모델에 relationship 추가 - `src/user_service/models/user.py` (profile, taste_preferences)
- [x] T007 models/__init__.py에 새 모델 export 추가 - `src/user_service/models/__init__.py`
- [x] T008 Alembic 마이그레이션 생성 - `src/user_service/alembic/versions/003_add_profile_preferences.py`
- [x] T009 [P] 프로필 서비스 레이어 생성 - `src/user_service/services/profile.py`
- [x] T010 [P] 취향 서비스 레이어 생성 - `src/user_service/services/preference.py`

**Checkpoint**: Foundation ready - User Story 구현 시작 가능

---

## Phase 3: User Story 1 - 프로필 조회 (Priority: P1) 🎯 MVP

**Goal**: 로그인한 사용자가 자신의 프로필 정보를 조회할 수 있다

**Independent Test**: `GET /api/v1/users/me` 호출 시 프로필 정보 반환

### Implementation for User Story 1

- [x] T011 [US1] ProfileService.get_profile(user_id) 구현 - `src/user_service/services/profile.py`
- [x] T012 [US1] GET /users/me 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T013 [US1] users 라우터를 main router에 등록 - `src/user_service/api/v1/router.py`

**Checkpoint**: User Story 1 완료 - 프로필 조회 독립 테스트 가능

---

## Phase 4: User Story 2 - 프로필 수정 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 자신의 이름과 프로필 이미지를 변경할 수 있다

**Independent Test**: `PUT /api/v1/users/me`로 displayName 변경 후 조회 시 변경값 확인

### Implementation for User Story 2

- [x] T014 [US2] ProfileService.update_profile(user_id, data) 구현 - `src/user_service/services/profile.py`
- [x] T015 [US2] PUT /users/me 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T016 [US2] 유효성 검사 (displayName 1-50자, URL 형식) - `src/user_service/schemas/profile.py`

**Checkpoint**: User Story 2 완료 - 프로필 수정 독립 테스트 가능

---

## Phase 5: User Story 3 - 식이 제한 및 알레르기 설정 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 식이 제한과 알레르기 정보를 설정하여 AI 보정 시 안전한 레시피 추천

**Independent Test**: `PUT /api/v1/users/me/preferences`로 allergies 설정 후 조회 시 확인

### Implementation for User Story 3

- [x] T017 [US3] PreferenceService.get_preferences(user_id) 구현 - `src/user_service/services/preference.py`
- [x] T018 [US3] PreferenceService.update_preferences(user_id, data) 구현 - `src/user_service/services/preference.py`
- [x] T019 [US3] GET /users/me/preferences 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T020 [US3] PUT /users/me/preferences 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T021 [P] [US3] GET /users/me/preferences/dietary-options 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T022 [P] [US3] GET /users/me/preferences/allergy-options 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T023 [US3] dietaryRestrictions, allergies Enum 유효성 검사 - `src/user_service/schemas/preference.py`

**Checkpoint**: User Story 3 완료 - 식이/알레르기 설정 독립 테스트 가능

---

## Phase 6: User Story 4 - 맛 취향 프로파일 설정 (Priority: P2)

**Goal**: 사용자가 단맛, 짠맛, 매운맛, 신맛 선호도를 설정하여 AI 레시피 보정 개인화

**Independent Test**: `PUT /api/v1/users/me/preferences`로 tastePreferences.overall 설정 후 확인

### Implementation for User Story 4

- [x] T024 [US4] TastePreference 서비스 로직 구현 - `src/user_service/services/preference.py`
  - overall 취향 생성/업데이트
  - 카테고리별 취향 생성/업데이트
  - 카테고리 취향은 overall 값 상속
- [x] T025 [US4] tastePreferences 요청/응답 스키마 - `src/user_service/schemas/preference.py`
- [x] T026 [US4] PUT /users/me/preferences에 tastePreferences 처리 추가 - `src/user_service/api/v1/users.py`
- [x] T027 [US4] 맛 취향 값 범위 검증 (1-5) - `src/user_service/schemas/preference.py`

**Checkpoint**: User Story 4 완료 - 맛 취향 설정 독립 테스트 가능

---

## Phase 7: User Story 5 - 기타 취향 정보 설정 (Priority: P3)

**Goal**: 요리 실력, 가구 인원, 선호 카테고리 등 부가 정보 설정

**Independent Test**: `PUT /api/v1/users/me/preferences`로 skillLevel, householdSize 설정 후 확인

### Implementation for User Story 5

- [x] T028 [US5] skillLevel, householdSize 처리 로직 - `src/user_service/services/preference.py`
- [x] T029 [US5] cuisinePreferences 처리 로직 - `src/user_service/services/preference.py`
- [x] T030 [P] [US5] GET /users/me/preferences/cuisine-options 엔드포인트 구현 - `src/user_service/api/v1/users.py`
- [x] T031 [US5] skillLevel (1-5), householdSize (1-20) 범위 검증 - `src/user_service/schemas/preference.py`
- [x] T032 [US5] cuisinePreferences 최대 10개 제한 검증 - `src/user_service/schemas/preference.py`

**Checkpoint**: User Story 5 완료 - 기타 취향 설정 독립 테스트 가능

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 전체 기능 품질 향상 및 공통 관심사 처리

- [x] T033 [P] 사용자 계정 생성 시 UserProfile 자동 생성 훅 - `src/user_service/services/user.py`, `src/user_service/services/oauth.py`
- [ ] T034 [P] Redis 캐싱 구현 (프로필 조회) - `src/user_service/services/profile.py` (선택적 최적화)
- [ ] T035 [P] UserPreferenceUpdated Kafka 이벤트 발행 - `src/user_service/events/preference.py` (선택적 최적화)
- [x] T036 API 로깅 및 에러 핸들링 강화 - `src/user_service/api/v1/users.py` (FastAPI 표준 방식)
- [ ] T037 quickstart.md 시나리오 검증 - 수동 테스트

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational) ─── BLOCKS ALL USER STORIES
    │
    ├──▶ Phase 3 (US1: 프로필 조회) ─ P1
    │
    ├──▶ Phase 4 (US2: 프로필 수정) ─ P1 (US1과 병렬 가능)
    │
    ├──▶ Phase 5 (US3: 식이/알레르기) ─ P1 (US1,2와 병렬 가능)
    │
    ├──▶ Phase 6 (US4: 맛 취향) ─ P2 (US3 완료 권장)
    │
    └──▶ Phase 7 (US5: 기타 취향) ─ P3 (US3,4 완료 권장)
            │
            ▼
      Phase 8 (Polish)
```

### Within Each Phase

- Setup: T001, T002, T003 병렬 실행 가능 [P]
- Foundational: T004 → T005 → T006 → T007 (순차), T009, T010 병렬 가능
- User Stories: 모델 → 서비스 → 엔드포인트 순서

### Parallel Opportunities

| Phase | Parallel Tasks |
|-------|----------------|
| Setup | T001, T002, T003 |
| Foundational | T009, T010 (서비스 레이어) |
| US3 | T021, T022 (options 엔드포인트) |
| US5 | T030 (cuisine-options) |
| Polish | T033, T034, T035 |

---

## Implementation Strategy

### MVP First (P1 User Stories)

1. ✅ Phase 1: Setup (Enum, Schemas)
2. ✅ Phase 2: Foundational (Models, Migration, Services)
3. ✅ Phase 3: US1 - 프로필 조회
4. ✅ Phase 4: US2 - 프로필 수정
5. ✅ Phase 5: US3 - 식이/알레르기 설정
6. **STOP and VALIDATE**: MVP 테스트

### Incremental Delivery

1. MVP 완료 → Deploy/Demo
2. Phase 6: US4 - 맛 취향 → Test → Deploy
3. Phase 7: US5 - 기타 취향 → Test → Deploy
4. Phase 8: Polish → Final Release

---

## Notes

- [P] 태스크는 서로 다른 파일, 의존성 없음
- 각 User Story는 독립적으로 테스트 가능해야 함
- US1, US2, US3은 P1이므로 MVP에 필수
- 커밋은 논리적 단위로 (예: Phase 또는 User Story 완료 시)
- quickstart.md 시나리오로 최종 검증
