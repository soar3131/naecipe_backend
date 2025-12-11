# Tasks: 레시피 저장 (원본 레시피 → 레시피북)

**Input**: Design documents from `/specs/008-save-recipe/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Tests**: TDD 방식 - 각 User Story의 테스트를 먼저 작성하고 구현
**Total Tasks**: 49개 (T001 ~ T049)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Database migration and shared model/schema definitions

- [X] T001 Alembic 마이그레이션 생성 (`alembic/versions/008_create_saved_recipes_table.py`)
- [X] T002 [P] SavedRecipe 모델 추가 (`app/cookbooks/models.py`)
- [X] T003 [P] SavedRecipe 스키마 추가 (`app/cookbooks/schemas.py`)
- [X] T004 [P] SavedRecipe 커스텀 예외 추가 (`app/cookbooks/exceptions.py`)
- [X] T005 테스트 픽스처 확장 (`tests/cookbooks/conftest.py`)

---

## Phase 2: Foundational (Blocking Prerequisites) ✅

**Purpose**: Core service infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 SavedRecipeService 클래스 스켈레톤 (`app/cookbooks/services.py`)
- [X] T007 [P] RecipeService 연동 - 레시피 존재 확인 메서드 (`app/recipes/services.py` 확장 또는 호출)
- [X] T008 [P] CookbookService 소유권 검증 재사용 확인 (`app/cookbooks/services.py`)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 원본 레시피 저장 (Priority: P1) 🎯 MVP ✅

**Goal**: 사용자가 원본 레시피를 레시피북에 저장하고, 선택적으로 메모를 추가할 수 있다

**Independent Test**: `POST /api/v1/cookbooks/{id}/recipes` → 201 Created + SavedRecipe 반환

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] 통합 테스트 - 레시피 저장 성공 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T010 [P] [US1] 통합 테스트 - 메모 포함 저장 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T011 [P] [US1] 통합 테스트 - 중복 저장 시 409 Conflict (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T012 [P] [US1] 통합 테스트 - 존재하지 않는 레시피 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T013 [P] [US1] 통합 테스트 - 다른 사용자 레시피북 접근 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T014 [P] [US1] 서비스 단위 테스트 - save_recipe 메서드 (`tests/cookbooks/test_saved_recipe_service.py`)

### Implementation for User Story 1

- [X] T015 [US1] SavedRecipeService.save_recipe() 구현 (`app/cookbooks/services.py`)
- [X] T016 [US1] POST /cookbooks/{cookbook_id}/recipes 엔드포인트 (`app/cookbooks/router.py`)
- [X] T017 [US1] 중복 저장 방지 로직 (IntegrityError 처리) (`app/cookbooks/services.py`)

**Checkpoint**: User Story 1 완료 - 레시피 저장 기능 독립 테스트 가능

---

## Phase 4: User Story 2 - 저장된 레시피 목록 조회 (Priority: P1) 🎯 MVP ✅

**Goal**: 사용자가 레시피북에 저장된 레시피 목록을 페이지네이션하여 조회할 수 있다

**Independent Test**: `GET /api/v1/cookbooks/{id}/recipes` → 200 OK + 목록 반환

### Tests for User Story 2

- [X] T018 [P] [US2] 통합 테스트 - 목록 조회 성공 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T019 [P] [US2] 통합 테스트 - 빈 목록 조회 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T020 [P] [US2] 통합 테스트 - 페이지네이션 동작 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T021 [P] [US2] 통합 테스트 - 다른 사용자 레시피북 접근 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T022 [P] [US2] 서비스 단위 테스트 - list_saved_recipes 메서드 (`tests/cookbooks/test_saved_recipe_service.py`)

### Implementation for User Story 2

- [X] T023 [US2] SavedRecipeService.list_saved_recipes() 구현 (`app/cookbooks/services.py`)
- [X] T024 [US2] GET /cookbooks/{cookbook_id}/recipes 엔드포인트 (`app/cookbooks/router.py`)
- [X] T025 [US2] Recipe 조인 로딩 최적화 (selectinload/joinedload) (`app/cookbooks/services.py`)

**Checkpoint**: User Stories 1 & 2 완료 - MVP 기능 테스트 가능

---

## Phase 5: User Story 3 - 저장된 레시피 상세 조회 (Priority: P2) ✅

**Goal**: 사용자가 저장된 레시피의 상세 정보(원본 레시피 포함)를 조회할 수 있다

**Independent Test**: `GET /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` → 200 OK + 상세 정보

### Tests for User Story 3

- [X] T026 [P] [US3] 통합 테스트 - 상세 조회 성공 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T027 [P] [US3] 통합 테스트 - 존재하지 않는 savedRecipeId 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T028 [P] [US3] 통합 테스트 - 다른 사용자 접근 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T029 [P] [US3] 서비스 단위 테스트 - get_saved_recipe 메서드 (`tests/cookbooks/test_saved_recipe_service.py`)

### Implementation for User Story 3

- [X] T030 [US3] SavedRecipeService.get_saved_recipe() 구현 (`app/cookbooks/services.py`)
- [X] T031 [US3] GET /cookbooks/{cookbook_id}/recipes/{saved_recipe_id} 엔드포인트 (`app/cookbooks/router.py`)

**Checkpoint**: User Story 3 완료 - 상세 조회 기능 독립 테스트 가능

---

## Phase 6: User Story 4 - 저장된 레시피 메모 수정 (Priority: P2) ✅

**Goal**: 사용자가 저장된 레시피의 개인 메모를 수정할 수 있다

**Independent Test**: `PATCH /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` → 200 OK + 수정된 정보

### Tests for User Story 4

- [X] T032 [P] [US4] 통합 테스트 - 메모 수정 성공 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T033 [P] [US4] 통합 테스트 - 빈 문자열로 메모 수정 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T034 [P] [US4] 통합 테스트 - null로 메모 수정 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T035 [P] [US4] 통합 테스트 - 다른 사용자 접근 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T036 [P] [US4] 서비스 단위 테스트 - update_saved_recipe 메서드 (`tests/cookbooks/test_saved_recipe_service.py`)

### Implementation for User Story 4

- [X] T037 [US4] SavedRecipeService.update_saved_recipe() 구현 (`app/cookbooks/services.py`)
- [X] T038 [US4] PATCH /cookbooks/{cookbook_id}/recipes/{saved_recipe_id} 엔드포인트 (`app/cookbooks/router.py`)

**Checkpoint**: User Story 4 완료 - 메모 수정 기능 독립 테스트 가능

---

## Phase 7: User Story 5 - 저장된 레시피 삭제 (Priority: P3) ✅

**Goal**: 사용자가 저장된 레시피를 삭제하고, 관련 보정 레시피도 CASCADE 삭제된다

**Independent Test**: `DELETE /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` → 204 No Content

### Tests for User Story 5

- [X] T039 [P] [US5] 통합 테스트 - 삭제 성공 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T040 [P] [US5] 통합 테스트 - 존재하지 않는 savedRecipeId 삭제 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T041 [P] [US5] 통합 테스트 - 다른 사용자 접근 404 (`tests/cookbooks/test_saved_recipe_crud.py`)
- [X] T042 [P] [US5] 서비스 단위 테스트 - delete_saved_recipe 메서드 (`tests/cookbooks/test_saved_recipe_service.py`)

### Implementation for User Story 5

- [X] T043 [US5] SavedRecipeService.delete_saved_recipe() 구현 (`app/cookbooks/services.py`)
- [X] T044 [US5] DELETE /cookbooks/{cookbook_id}/recipes/{saved_recipe_id} 엔드포인트 (`app/cookbooks/router.py`)

**Checkpoint**: 모든 User Stories 완료 - 전체 기능 독립 테스트 가능

---

## Phase 8: Polish & Cross-Cutting Concerns ✅

**Purpose**: Improvements that affect multiple user stories

- [X] T045 [P] 구조화 로깅 추가 (`app/cookbooks/services.py`, `app/cookbooks/router.py`)
- [X] T046 [P] OpenAPI 문서 주석 보강 (`app/cookbooks/router.py`)
- [X] T047 전체 테스트 실행 및 커버리지 검증 (`pytest tests/cookbooks/test_saved_recipe*.py --cov`)
- [X] T048 quickstart.md 시나리오 검증 (수동 또는 자동 테스트)
- [X] T049 [P] 성능 벤치마크 테스트 - SC-001 저장 <500ms, SC-002 목록 <200ms 검증

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Phase 2 completion
  - P1 stories (US1, US2) first, then P2 (US3, US4), then P3 (US5)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Phase 2 - May benefit from US1 test fixtures
- **User Story 3 (P2)**: Can start after Phase 2 - Uses SavedRecipe created in US1
- **User Story 4 (P2)**: Can start after Phase 2 - Uses SavedRecipe created in US1
- **User Story 5 (P3)**: Can start after Phase 2 - Uses SavedRecipe created in US1

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Service methods before router endpoints
- Core implementation before edge cases

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- All tests for a user story marked [P] can run in parallel
- Phase 3-4 (US1, US2) can theoretically run in parallel as P1 stories
- Phase 5-6 (US3, US4) can run in parallel as P2 stories

---

## Implementation Strategy

### MVP First (P1 Only: US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Save Recipe)
4. Complete Phase 4: User Story 2 (List Recipes)
5. **STOP and VALIDATE**: Test MVP independently
6. Deploy/demo if ready

### Full Implementation

1. Complete MVP (Phase 1-4)
2. Complete Phase 5: User Story 3 (Detail View)
3. Complete Phase 6: User Story 4 (Update Memo)
4. Complete Phase 7: User Story 5 (Delete)
5. Complete Phase 8: Polish
6. Final validation with quickstart.md

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD: 테스트 먼저 작성 후 실패 확인, 그 다음 구현
- Constitution III 준수: Contract/Integration 테스트 필수
- Commit after each phase or logical group
- CASCADE 삭제는 RecipeVariation이 없으므로 현재는 SavedRecipe만 삭제됨 (SPEC-009에서 추가)
