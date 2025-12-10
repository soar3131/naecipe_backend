# Tasks: 원본 레시피 기본 CRUD

**Input**: Design documents from `/specs/004-recipe-basic-crud/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Tests**: TDD 접근법 적용 - Constitution III (TDD) 준수

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md, this project uses microservices structure:
- **Service Root**: `services/recipe-service/`
- **Source**: `services/recipe-service/src/`
- **Tests**: `services/recipe-service/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Recipe Service 프로젝트 초기화 및 기본 구조 설정

- [x] T001 Create recipe-service directory structure per plan.md in `services/recipe-service/`
- [x] T002 Initialize Python project with pyproject.toml in `services/recipe-service/pyproject.toml` (FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+, redis[hiredis], pytest, pytest-asyncio, httpx)
- [x] T003 [P] Create .env.example and config module in `services/recipe-service/src/config.py`
- [x] T004 [P] Configure linting (ruff) and formatting (black) in `services/recipe-service/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story가 의존하는 핵심 인프라 구현

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create database connection and session management in `services/recipe-service/src/database.py`
- [x] T006 [P] Create base SQLAlchemy model class in `services/recipe-service/src/models/base.py`
- [x] T007 [P] Create common Pydantic schemas (error response, pagination) in `services/recipe-service/src/schemas/common.py`
- [x] T008 [P] Implement Redis cache utility (Cache-Aside pattern) in `services/recipe-service/src/cache/redis_cache.py`
- [x] T009 [P] Create cursor-based pagination utility in `services/recipe-service/src/schemas/pagination.py`
- [x] T010 Create FastAPI app initialization with routers in `services/recipe-service/src/main.py`
- [x] T011 [P] Setup error handling middleware and exception handlers in `services/recipe-service/src/middleware/error_handler.py`
- [x] T012 [P] Configure structured logging (JSON format) in `services/recipe-service/src/logging_config.py`
- [x] T013 Create test fixtures and conftest in `services/recipe-service/tests/conftest.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 레시피 상세 조회 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 레시피 ID로 상세 정보(제목, 설명, 재료, 조리 단계, 요리사, 태그)를 조회

**Independent Test**: `GET /recipes/{id}` 요청 시 모든 연관 정보가 포함된 응답 반환

### Models for User Story 1

- [x] T014 [P] [US1] Create Chef model in `services/recipe-service/src/models/chef.py`
- [x] T015 [P] [US1] Create ChefPlatform model in `services/recipe-service/src/models/chef.py`
- [x] T016 [P] [US1] Create Recipe model in `services/recipe-service/src/models/recipe.py`
- [x] T017 [P] [US1] Create RecipeIngredient model in `services/recipe-service/src/models/ingredient.py`
- [x] T018 [P] [US1] Create CookingStep model in `services/recipe-service/src/models/step.py`
- [x] T019 [P] [US1] Create Tag and RecipeTag models in `services/recipe-service/src/models/tag.py`
- [x] T020 [US1] Create models __init__.py with all exports in `services/recipe-service/src/models/__init__.py`

### Schemas for User Story 1

- [x] T021 [P] [US1] Create RecipeDetail Pydantic schema in `services/recipe-service/src/schemas/recipe.py`
- [x] T022 [P] [US1] Create Ingredient schema in `services/recipe-service/src/schemas/recipe.py`
- [x] T023 [P] [US1] Create CookingStep schema in `services/recipe-service/src/schemas/recipe.py`
- [x] T024 [P] [US1] Create Tag schema in `services/recipe-service/src/schemas/recipe.py`
- [x] T025 [P] [US1] Create ChefSummary schema in `services/recipe-service/src/schemas/chef.py`

### Service for User Story 1

- [x] T026 [US1] Implement RecipeService.get_by_id() with eager loading in `services/recipe-service/src/services/recipe_service.py`
- [x] T027 [US1] Add Redis caching to RecipeService.get_by_id() in `services/recipe-service/src/services/recipe_service.py`

### API for User Story 1

- [x] T028 [US1] Implement GET /recipes/{id} endpoint in `services/recipe-service/src/api/recipes.py`
- [x] T029 [US1] Add 404 error handling for non-existent recipe in `services/recipe-service/src/api/recipes.py`

### Tests for User Story 1

- [x] T030 [P] [US1] Contract test for GET /recipes/{id} in `services/recipe-service/tests/contract/test_recipes_api.py`
- [x] T031 [P] [US1] Unit test for RecipeService.get_by_id() in `services/recipe-service/tests/unit/test_recipe_service.py`

**Checkpoint**: User Story 1 완료 - 레시피 상세 조회 기능 독립적으로 테스트 가능

---

## Phase 4: User Story 2 - 레시피 목록 조회 (Priority: P1)

**Goal**: 사용자가 레시피 목록을 커서 기반 페이지네이션으로 탐색

**Independent Test**: `GET /recipes` 요청 시 페이지네이션된 결과와 다음 페이지 커서 반환

### Schemas for User Story 2

- [x] T032 [P] [US2] Create RecipeListItem schema (간략 버전) in `services/recipe-service/src/schemas/recipe.py`
- [x] T033 [P] [US2] Create RecipeListResponse schema in `services/recipe-service/src/schemas/recipe.py`

### Service for User Story 2

- [x] T034 [US2] Implement RecipeService.list_recipes() with cursor pagination in `services/recipe-service/src/services/recipe_service.py`
- [x] T035 [US2] Add is_active filter to exclude inactive recipes in `services/recipe-service/src/services/recipe_service.py`

### API for User Story 2

- [x] T036 [US2] Implement GET /recipes endpoint with pagination in `services/recipe-service/src/api/recipes.py`
- [x] T037 [US2] Add 400 error handling for invalid cursor in `services/recipe-service/src/api/recipes.py`

### Tests for User Story 2

- [x] T038 [P] [US2] Contract test for GET /recipes in `services/recipe-service/tests/contract/test_recipes_api.py`
- [x] T039 [P] [US2] Unit test for RecipeService.list_recipes() in `services/recipe-service/tests/unit/test_recipe_service.py`

**Checkpoint**: User Story 2 완료 - 레시피 목록 조회 기능 독립적으로 테스트 가능

---

## Phase 5: User Story 3 - 인기 레시피 조회 (Priority: P2)

**Goal**: 사용자가 인기도 점수 기준으로 정렬된 인기 레시피 조회

**Independent Test**: `GET /recipes/popular` 요청 시 exposure_score 기준 내림차순 정렬된 결과 반환

### Service for User Story 3

- [x] T040 [US3] Implement RecipeService.get_popular_recipes() with exposure_score sorting in `services/recipe-service/src/services/recipe_service.py`
- [x] T041 [US3] Add category filter to get_popular_recipes() in `services/recipe-service/src/services/recipe_service.py`
- [x] T042 [US3] Add Redis caching for popular recipes in `services/recipe-service/src/services/recipe_service.py`

### API for User Story 3

- [x] T043 [US3] Implement GET /recipes/popular endpoint in `services/recipe-service/src/api/recipes.py`

### Tests for User Story 3

- [x] T044 [P] [US3] Contract test for GET /recipes/popular in `services/recipe-service/tests/contract/test_recipes_api.py`
- [x] T045 [P] [US3] Unit test for RecipeService.get_popular_recipes() in `services/recipe-service/tests/unit/test_recipe_service.py`

**Checkpoint**: User Story 3 완료 - 인기 레시피 조회 기능 독립적으로 테스트 가능

---

## Phase 6: User Story 4 - 요리사 목록 및 상세 조회 (Priority: P2)

**Goal**: 사용자가 요리사 목록/상세/인기 요리사 조회

**Independent Test**: `GET /chefs`, `GET /chefs/{id}`, `GET /chefs/popular` 요청 시 올바른 요리사 정보 반환

### Schemas for User Story 4

- [x] T046 [P] [US4] Create ChefListItem schema in `services/recipe-service/src/schemas/chef.py`
- [x] T047 [P] [US4] Create ChefDetail schema in `services/recipe-service/src/schemas/chef.py`
- [x] T048 [P] [US4] Create ChefPlatform schema in `services/recipe-service/src/schemas/chef.py`
- [x] T049 [P] [US4] Create ChefListResponse schema in `services/recipe-service/src/schemas/chef.py`

### Service for User Story 4

- [x] T050 [US4] Implement ChefService.list_chefs() with cursor pagination in `services/recipe-service/src/services/chef_service.py`
- [x] T051 [US4] Implement ChefService.get_by_id() with eager loading in `services/recipe-service/src/services/chef_service.py`
- [x] T052 [US4] Implement ChefService.get_popular_chefs() in `services/recipe-service/src/services/chef_service.py`
- [x] T053 [US4] Add Redis caching to ChefService methods in `services/recipe-service/src/services/chef_service.py`

### API for User Story 4

- [x] T054 [US4] Implement GET /chefs endpoint in `services/recipe-service/src/api/chefs.py`
- [x] T055 [US4] Implement GET /chefs/{id} endpoint in `services/recipe-service/src/api/chefs.py`
- [x] T056 [US4] Implement GET /chefs/popular endpoint in `services/recipe-service/src/api/chefs.py`
- [x] T057 [US4] Add 404 error handling for non-existent chef in `services/recipe-service/src/api/chefs.py`

### Tests for User Story 4

- [x] T058 [P] [US4] Contract test for GET /chefs in `services/recipe-service/tests/contract/test_chefs_api.py`
- [x] T059 [P] [US4] Contract test for GET /chefs/{id} in `services/recipe-service/tests/contract/test_chefs_api.py`
- [x] T060 [P] [US4] Unit test for ChefService methods in `services/recipe-service/tests/unit/test_chef_service.py`

**Checkpoint**: User Story 4 완료 - 요리사 조회 기능 독립적으로 테스트 가능

---

## Phase 7: User Story 5 - 요리사별 레시피 조회 (Priority: P2)

**Goal**: 사용자가 특정 요리사의 레시피 목록 조회

**Independent Test**: `GET /chefs/{id}/recipes` 요청 시 해당 요리사의 레시피만 반환

### Service for User Story 5

- [x] T061 [US5] Implement RecipeService.get_recipes_by_chef() with pagination in `services/recipe-service/src/services/recipe_service.py`

### API for User Story 5

- [x] T062 [US5] Implement GET /chefs/{id}/recipes endpoint in `services/recipe-service/src/api/chefs.py`
- [x] T063 [US5] Handle empty recipe list case in `services/recipe-service/src/api/chefs.py`

### Tests for User Story 5

- [x] T064 [P] [US5] Contract test for GET /chefs/{id}/recipes in `services/recipe-service/tests/contract/test_chefs_api.py`
- [x] T065 [P] [US5] Unit test for RecipeService.get_recipes_by_chef() in `services/recipe-service/tests/unit/test_recipe_service.py`

**Checkpoint**: User Story 5 완료 - 요리사별 레시피 조회 기능 독립적으로 테스트 가능

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 품질 개선 및 공통 관심사 처리

- [x] T066 [P] Create Alembic migration for all models in `services/recipe-service/alembic/versions/001_initial_schema.py`
- [x] T067 [P] Add OpenAPI schema export/validation in `services/recipe-service/src/main.py`
- [x] T068 [P] Create Dockerfile for recipe-service in `services/recipe-service/Dockerfile`
- [x] T069 [P] Add health check endpoint (/health, /ready) in `services/recipe-service/src/api/health.py`
- [x] T070 [P] Integration test for full user journey in `services/recipe-service/tests/integration/test_full_journey.py`
- [x] T071 Run quickstart.md validation - verify all scenarios work

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1) and US2 (P1) share models, recommend US1 first
  - US3 (P2), US4 (P2), US5 (P2) can proceed after US1 models exist
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Dependencies | Can Start After |
|-------|----------|--------------|-----------------|
| US1 - 레시피 상세 조회 | P1 | Foundational | Phase 2 |
| US2 - 레시피 목록 조회 | P1 | US1 models | T020 (models) |
| US3 - 인기 레시피 조회 | P2 | US2 (list logic) | T039 |
| US4 - 요리사 목록/상세 | P2 | US1 (Chef model) | T020 |
| US5 - 요리사별 레시피 | P2 | US4 + US2 | T060 + T039 |

### Within Each User Story

1. Models before Schemas
2. Schemas before Services
3. Services before APIs
4. APIs before Tests (또는 TDD 적용 시 Tests first)

### Parallel Opportunities

**Phase 2 (Foundational)**:
```
T005 (database) → T006, T007, T008, T009, T011, T012 can run in parallel
```

**Phase 3 (US1 Models)**:
```
T014, T015, T016, T017, T018, T019 can all run in parallel
```

**Phase 3 (US1 Schemas)**:
```
T021, T022, T023, T024, T025 can all run in parallel
```

**Phase 3 (US1 Tests)**:
```
T030, T031 can run in parallel
```

---

## Parallel Example: User Story 1

```bash
# Launch all models for User Story 1 together:
Task: "Create Chef model in services/recipe-service/src/models/chef.py"
Task: "Create ChefPlatform model in services/recipe-service/src/models/chef.py"
Task: "Create Recipe model in services/recipe-service/src/models/recipe.py"
Task: "Create RecipeIngredient model in services/recipe-service/src/models/ingredient.py"
Task: "Create CookingStep model in services/recipe-service/src/models/step.py"
Task: "Create Tag and RecipeTag models in services/recipe-service/src/models/tag.py"

# After models complete, launch all schemas together:
Task: "Create RecipeDetail Pydantic schema in services/recipe-service/src/schemas/recipe.py"
Task: "Create Ingredient schema in services/recipe-service/src/schemas/recipe.py"
Task: "Create CookingStep schema in services/recipe-service/src/schemas/recipe.py"
Task: "Create Tag schema in services/recipe-service/src/schemas/recipe.py"
Task: "Create ChefSummary schema in services/recipe-service/src/schemas/chef.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 - 레시피 상세 조회
4. Complete Phase 4: User Story 2 - 레시피 목록 조회
5. **STOP and VALIDATE**: Test US1 + US2 independently
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test → Deploy (레시피 상세 조회 MVP!)
3. Add US2 → Test → Deploy (레시피 목록 추가)
4. Add US3 → Test → Deploy (인기 레시피 추가)
5. Add US4 + US5 → Test → Deploy (요리사 기능 추가)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With 2 developers after Foundational:
- Developer A: US1 → US3
- Developer B: US2 → US4 → US5

---

## Summary

| Phase | Tasks | Parallel | Description |
|-------|-------|----------|-------------|
| 1. Setup | 4 | 2 | 프로젝트 초기화 |
| 2. Foundational | 9 | 7 | 핵심 인프라 |
| 3. US1 (P1) | 18 | 14 | 레시피 상세 조회 |
| 4. US2 (P1) | 8 | 4 | 레시피 목록 조회 |
| 5. US3 (P2) | 6 | 2 | 인기 레시피 조회 |
| 6. US4 (P2) | 15 | 7 | 요리사 목록/상세 |
| 7. US5 (P2) | 5 | 2 | 요리사별 레시피 |
| 8. Polish | 6 | 5 | 품질 개선 |
| **Total** | **71** | **43** | - |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Redis cache keys: `recipe:{id}` (1h), `recipes:popular:{category}` (10m), `chef:{id}` (1h)
