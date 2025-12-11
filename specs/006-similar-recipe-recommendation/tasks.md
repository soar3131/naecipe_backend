# Tasks: 유사 레시피 추천

**Input**: Design documents from `/specs/006-similar-recipe-recommendation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/similar-recipes-api.yaml

**Tests**: TDD 방식으로 테스트 우선 작성 (Constitution III 준수)

**Organization**: 태스크는 유저 스토리별로 그룹화하여 독립적으로 구현/테스트 가능

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 해당 유저 스토리 (US1, US2, US3, US4)
- 정확한 파일 경로 포함

## Path Conventions

- **Backend**: `app/` 기반 모듈러 모놀리스
- **Tests**: `tests/recipes/`

---

## Phase 1: Setup (공유 인프라)

**Purpose**: 유사 레시피 추천 기능을 위한 스키마 및 서비스 기반 구조 생성

- [x] T001 [P] 유사 레시피 Pydantic 스키마 추가 in `app/recipes/schemas.py`
- [x] T002 [P] 커서 기반 페이지네이션 유틸리티 추가 in `shared/utils/pagination.py`
- [x] T003 [P] 유사 레시피 캐시 키 상수 추가 in `app/recipes/services.py` (RecipeCacheKeys 클래스 확장)

---

## Phase 2: Foundational (블로킹 전제조건)

**Purpose**: 모든 유저 스토리 구현 전 완료해야 하는 핵심 인프라

**⚠️ CRITICAL**: 이 단계가 완료되기 전에 유저 스토리 작업을 시작할 수 없음

- [x] T004 `SimilarRecipeService` 클래스 기본 구조 생성 in `app/recipes/services.py`
- [x] T005 유사 레시피 라우터 기본 구조 생성 in `app/recipes/router.py` (엔드포인트 스텁)
- [x] T006 [P] 테스트 픽스처 생성 (샘플 레시피, 태그, 재료) in `tests/recipes/conftest.py`

**Checkpoint**: 기반 구조 완료 - 유저 스토리별 구현 시작 가능

---

## Phase 3: User Story 1 - 유사 레시피 조회 (Priority: P1) 🎯 MVP

**Goal**: 특정 레시피와 콘텐츠 기반으로 유사한 레시피 목록 반환 (태그 40% + 재료 40% + 조리법 20% 유사도)

**Independent Test**: `GET /api/v1/recipes/{id}/similar` 호출 시 유사도 순 레시피 목록 반환

### Tests for User Story 1

- [x] T007 [P] [US1] 유사 레시피 API 테스트 작성 in `tests/recipes/test_similar_recipes.py`
- [x] T008 [P] [US1] 유사 레시피 서비스 단위 테스트 작성 in `tests/recipes/test_similar_service.py`

### Implementation for User Story 1

- [x] T009 [US1] `SimilarRecipeItem` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T010 [US1] `SimilarRecipeListResponse` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T011 [US1] 태그 기반 유사도 계산 SQL 쿼리 구현 in `app/recipes/services.py`
- [x] T012 [US1] 재료 기반 유사도 계산 SQL 쿼리 구현 in `app/recipes/services.py`
- [x] T013 [US1] 조리법 기반 유사도 계산 로직 구현 in `app/recipes/services.py`
- [x] T014 [US1] 통합 유사도 계산 메서드 `get_similar_recipes()` 구현 in `app/recipes/services.py`
- [x] T015 [US1] Redis 캐싱 통합 (TTL 10분) in `app/recipes/services.py`
- [x] T016 [US1] `GET /recipes/{recipe_id}/similar` 엔드포인트 구현 in `app/recipes/router.py`
- [x] T017 [US1] 엣지 케이스 처리 (태그 없음, 유사 레시피 없음) in `app/recipes/services.py`

**Checkpoint**: 유사 레시피 조회 API 완전 동작, 독립적으로 테스트 가능

---

## Phase 4: User Story 2 - 같은 요리사 레시피 조회 (Priority: P2)

**Goal**: 동일 요리사의 다른 레시피 목록 반환 (현재 레시피 제외)

**Independent Test**: `GET /api/v1/recipes/{id}/same-chef` 호출 시 같은 요리사 레시피 목록 반환

### Tests for User Story 2

- [x] T018 [P] [US2] 같은 요리사 레시피 API 테스트 작성 in `tests/recipes/test_same_chef_recipes.py`

### Implementation for User Story 2

- [x] T019 [US2] `SameChefRecipeItem` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T020 [US2] `SameChefRecipeListResponse` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T021 [US2] `get_same_chef_recipes()` 메서드 구현 in `app/recipes/services.py`
- [x] T022 [US2] Redis 캐싱 통합 (TTL 10분) in `app/recipes/services.py`
- [x] T023 [US2] `GET /recipes/{recipe_id}/same-chef` 엔드포인트 구현 in `app/recipes/router.py`
- [x] T024 [US2] 엣지 케이스 처리 (요리사 없음, 레시피 1개만 있음) in `app/recipes/services.py`

**Checkpoint**: User Story 1, 2 모두 독립적으로 동작

---

## Phase 5: User Story 3 - 태그 기반 관련 레시피 조회 (Priority: P2)

**Goal**: 공유 태그 수가 많은 순으로 관련 레시피 반환

**Independent Test**: `GET /api/v1/recipes/{id}/related-by-tags` 호출 시 태그 겹침 순 레시피 목록 반환

### Tests for User Story 3

- [x] T025 [P] [US3] 태그 기반 관련 레시피 API 테스트 작성 in `tests/recipes/test_related_by_tags.py`

### Implementation for User Story 3

- [x] T026 [US3] `RelatedByTagsItem` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T027 [US3] `RelatedByTagsListResponse` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T028 [US3] `get_related_by_tags()` 메서드 구현 in `app/recipes/services.py`
- [x] T029 [US3] Redis 캐싱 통합 (TTL 10분) in `app/recipes/services.py`
- [x] T030 [US3] `GET /recipes/{recipe_id}/related-by-tags` 엔드포인트 구현 in `app/recipes/router.py`
- [x] T031 [US3] 엣지 케이스 처리 (태그 없음) in `app/recipes/services.py`

**Checkpoint**: User Story 1, 2, 3 모두 독립적으로 동작

---

## Phase 6: User Story 4 - 카테고리 인기 레시피 조회 (Priority: P3)

**Goal**: 동일 카테고리 내 조회수 기준 인기 레시피 반환

**Independent Test**: `GET /api/v1/recipes/{id}/category-popular` 호출 시 카테고리 내 인기 레시피 목록 반환

### Tests for User Story 4

- [x] T032 [P] [US4] 카테고리 인기 레시피 API 테스트 작성 in `tests/recipes/test_category_popular.py`

### Implementation for User Story 4

- [x] T033 [US4] `CategoryPopularItem` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T034 [US4] `CategoryPopularListResponse` 응답 스키마 구현 in `app/recipes/schemas.py`
- [x] T035 [US4] `get_category_popular()` 메서드 구현 in `app/recipes/services.py`
- [x] T036 [US4] Redis 캐싱 통합 (TTL 10분, 카테고리별 키) in `app/recipes/services.py`
- [x] T037 [US4] `GET /recipes/{recipe_id}/category-popular` 엔드포인트 구현 in `app/recipes/router.py`
- [x] T038 [US4] 엣지 케이스 처리 (카테고리 없음) in `app/recipes/services.py`

**Checkpoint**: 모든 유저 스토리 독립적으로 동작

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 전체 기능에 영향을 미치는 개선 사항

- [x] T039 [P] 캐시 무효화 로직 구현 (레시피 수정/삭제 시) in `app/recipes/services.py`
- [x] T040 [P] 구조화된 로깅 추가 (CloudWatch 연동) in `app/recipes/services.py`
- [x] T041 [P] 성능 테스트 (응답 시간 300ms 이내 검증) in `tests/recipes/test_performance.py`
- [x] T042 quickstart.md 시나리오 검증 실행
- [x] T043 [P] API 문서 업데이트 (OpenAPI 자동 생성 확인)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 - 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 필요 - 모든 유저 스토리 블로킹
- **User Stories (Phase 3-6)**: Foundational 완료 필요
  - 유저 스토리는 병렬 진행 가능 (팀 구성원이 있을 경우)
  - 또는 우선순위 순서로 순차 진행 (P1 → P2 → P3)
- **Polish (Phase 7)**: 모든 유저 스토리 완료 필요

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 완료 후 시작 - 다른 스토리에 의존 없음
- **User Story 2 (P2)**: Foundational 완료 후 시작 - US1과 독립적으로 테스트 가능
- **User Story 3 (P2)**: Foundational 완료 후 시작 - US1/US2와 독립적으로 테스트 가능
- **User Story 4 (P3)**: Foundational 완료 후 시작 - 모든 이전 스토리와 독립적으로 테스트 가능

### Within Each User Story

- 테스트 먼저 작성 후 실패 확인
- 스키마 → 서비스 → 엔드포인트 순서
- 핵심 구현 후 캐싱 통합
- 마지막에 엣지 케이스 처리

### Parallel Opportunities

**Phase 1 (Setup)**:
```
병렬 가능: T001, T002, T003
```

**Phase 2 (Foundational)**:
```
순차: T004 → T005
병렬 가능: T006 (테스트 픽스처)
```

**Phase 3 (User Story 1)**:
```
병렬 가능: T007, T008 (테스트)
순차: T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017
```

**Phase 4-6 (User Story 2-4)**:
```
각 스토리 내에서 순차 진행
스토리 간에는 병렬 진행 가능
```

---

## Parallel Example: Setup Phase

```bash
# Phase 1의 모든 태스크 병렬 실행:
Task: "유사 레시피 Pydantic 스키마 추가 in app/recipes/schemas.py"
Task: "커서 기반 페이지네이션 유틸리티 추가 in shared/utils/pagination.py"
Task: "유사 레시피 캐시 키 상수 추가 in app/recipes/services.py"
```

## Parallel Example: User Story 1 Tests

```bash
# US1 테스트 병렬 작성:
Task: "유사 레시피 API 테스트 작성 in tests/recipes/test_similar_recipes.py"
Task: "유사 레시피 서비스 단위 테스트 작성 in tests/recipes/test_similar_service.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 완료: Setup
2. Phase 2 완료: Foundational (CRITICAL - 모든 스토리 블로킹)
3. Phase 3 완료: User Story 1
4. **STOP and VALIDATE**: US1 독립 테스트
5. 준비되면 배포/데모

### Incremental Delivery

1. Setup + Foundational 완료 → 기반 준비
2. User Story 1 추가 → 독립 테스트 → 배포/데모 (MVP!)
3. User Story 2 추가 → 독립 테스트 → 배포/데모
4. User Story 3 추가 → 독립 테스트 → 배포/데모
5. User Story 4 추가 → 독립 테스트 → 배포/데모
6. 각 스토리는 이전 스토리를 깨뜨리지 않고 가치를 추가

### Parallel Team Strategy

여러 개발자가 있을 경우:

1. 팀이 함께 Setup + Foundational 완료
2. Foundational 완료 후:
   - 개발자 A: User Story 1 (P1)
   - 개발자 B: User Story 2 (P2)
   - 개발자 C: User Story 3 + 4 (P2, P3)
3. 스토리별로 독립적으로 완료 및 통합

---

## Notes

- [P] 태스크 = 다른 파일, 의존성 없음
- [Story] 라벨은 태스크를 특정 유저 스토리에 매핑
- 각 유저 스토리는 독립적으로 완료 및 테스트 가능
- 구현 전 테스트 실패 확인
- 각 태스크 또는 논리적 그룹 완료 후 커밋
- 어느 체크포인트에서든 멈추고 스토리 독립 검증 가능
- 피해야 할 것: 모호한 태스크, 같은 파일 충돌, 독립성을 깨는 스토리 간 의존성
