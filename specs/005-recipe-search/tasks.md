# Tasks: 원본 레시피 검색

**Input**: Design documents from `/specs/005-recipe-search/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included based on Constitution (III. TDD) requirement - Contract/Integration 테스트 필수

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Microservices**: `services/recipe-service/src/` (recipe-service 8001)
- **Tests**: `services/recipe-service/tests/`
- **Shared**: `shared/schemas/`, `shared/utils/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 검색 기능을 위한 기본 구조 및 설정

- [X] T001 Create search feature directory structure in services/recipe-service/src/api/search/
- [X] T002 [P] Create search Pydantic schemas in services/recipe-service/src/schemas/search.py (SearchQueryParams, SearchResult, SearchResultItem, ChefSummary, TagSummary)
- [X] T003 [P] Create cursor encoding utilities in services/recipe-service/src/utils/cursor.py (encode_cursor, decode_cursor)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 모든 User Story에서 사용하는 검색 기반 인프라

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add search indexes migration in services/recipe-service/alembic/versions/ (idx_recipes_cook_time_sort, idx_recipes_view_count_sort, idx_recipes_created_at_sort, idx_recipe_ingredients_name_pattern, idx_chefs_name_pattern, idx_recipes_difficulty, idx_recipes_cook_time_range)
- [X] T005 [P] Create search service base in services/recipe-service/src/services/search_service.py (SearchService class skeleton)
- [X] T006 [P] Create search router in services/recipe-service/src/api/routes/search.py (GET /recipes/search endpoint skeleton)
- [X] T007 Register search router in services/recipe-service/src/api/routes/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 키워드로 레시피 검색 (Priority: P1) 🎯 MVP

**Goal**: 사용자가 검색창에 키워드를 입력하여 레시피를 찾을 수 있음 (제목, 설명, 재료명, 요리사명 검색)

**Independent Test**: `GET /recipes/search?q=김치` 호출 시 "김치"가 포함된 레시피 목록 반환

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test for keyword search in services/recipe-service/tests/contract/test_search_keyword.py (검색어 매칭, 빈 결과, 특수문자 처리)
- [X] T009 [P] [US1] Integration test for keyword search in services/recipe-service/tests/integration/test_search_keyword.py (제목/설명/재료/요리사 매칭 검증)

### Implementation for User Story 1

- [X] T010 [US1] Implement keyword search logic in services/recipe-service/src/services/search_service.py (build_keyword_conditions: title, description ILIKE)
- [X] T011 [US1] Implement ingredient name search in services/recipe-service/src/services/search_service.py (ingredient_subquery: RecipeIngredient.name ILIKE)
- [X] T012 [US1] Implement chef name search in services/recipe-service/src/services/search_service.py (chef_subquery: Chef.name ILIKE)
- [X] T013 [US1] Implement combined OR condition in services/recipe-service/src/services/search_service.py (or_(*keyword_conditions))
- [X] T014 [US1] Implement search endpoint handler in services/recipe-service/src/api/routes/search.py (GET /recipes/search?q={keyword})
- [X] T015 [US1] Add input validation for search query in services/recipe-service/src/schemas/search.py (max_length=100, sanitize_keyword validator)
- [X] T016 [US1] Add error handling for INVALID_SEARCH_QUERY in services/recipe-service/src/api/routes/search.py

**Checkpoint**: User Story 1 완료 - 키워드 검색으로 레시피 검색 가능

---

## Phase 4: User Story 2 - 필터링으로 검색 결과 좁히기 (Priority: P1)

**Goal**: 난이도, 조리시간, 태그, 요리사로 검색 결과 필터링

**Independent Test**: `GET /recipes/search?difficulty=easy&max_cook_time=30&tag=한식` 호출 시 조건 만족하는 레시피만 반환

### Tests for User Story 2

- [X] T017 [P] [US2] Contract test for filtering in services/recipe-service/tests/contract/test_search_filter.py (각 필터별 테스트, AND 조합, 빈 결과)
- [X] T018 [P] [US2] Integration test for filtering in services/recipe-service/tests/integration/test_search_filter.py (필터 조합 검증)

### Implementation for User Story 2

- [X] T019 [US2] Implement difficulty filter in services/recipe-service/src/services/search_service.py (Recipe.difficulty == difficulty)
- [X] T020 [US2] Implement max_cook_time filter in services/recipe-service/src/services/search_service.py (Recipe.cook_time_minutes <= max_cook_time)
- [X] T021 [US2] Implement chef_id filter in services/recipe-service/src/services/search_service.py (Recipe.chef_id == chef_id)
- [X] T022 [US2] Implement tag filter in services/recipe-service/src/services/search_service.py (tag_subquery: RecipeTag.tag_id, Tag.name)
- [X] T023 [US2] Update search endpoint to accept filter params in services/recipe-service/src/api/routes/search.py
- [X] T024 [US2] Add validation for filter values in services/recipe-service/src/schemas/search.py (difficulty enum, max_cook_time ge=1, chef_id UUID)
- [X] T025 [US2] Add error handling for INVALID_FILTER_VALUE in services/recipe-service/src/api/routes/search.py

**Checkpoint**: User Story 2 완료 - 키워드 검색 + 필터링 가능

---

## Phase 5: User Story 3 - 검색 결과 정렬 (Priority: P2)

**Goal**: 검색 결과를 relevance, latest, cook_time, popularity 기준으로 정렬

**Independent Test**: `GET /recipes/search?sort=latest` 호출 시 생성일 내림차순 정렬된 결과 반환

### Tests for User Story 3

- [X] T026 [P] [US3] Contract test for sorting in services/recipe-service/tests/contract/test_search_sort.py (각 정렬 기준별 테스트, 기본값 테스트)
- [X] T027 [P] [US3] Integration test for sorting in services/recipe-service/tests/integration/test_search_sort.py (정렬 순서 검증)

### Implementation for User Story 3

- [X] T028 [US3] Implement relevance sort in services/recipe-service/src/services/search_service.py (ORDER BY exposure_score DESC, id DESC)
- [X] T029 [US3] Implement latest sort in services/recipe-service/src/services/search_service.py (ORDER BY created_at DESC, id DESC)
- [X] T030 [US3] Implement cook_time sort in services/recipe-service/src/services/search_service.py (ORDER BY cook_time_minutes ASC NULLS LAST, id ASC)
- [X] T031 [US3] Implement popularity sort in services/recipe-service/src/services/search_service.py (ORDER BY view_count DESC, id DESC)
- [X] T032 [US3] Create apply_sort_and_cursor helper in services/recipe-service/src/services/search_service.py
- [X] T033 [US3] Update search endpoint to accept sort param in services/recipe-service/src/api/routes/search.py
- [X] T034 [US3] Add validation for sort option in services/recipe-service/src/schemas/search.py (Literal["relevance", "latest", "cook_time", "popularity"])
- [X] T035 [US3] Add error handling for INVALID_SORT_OPTION in services/recipe-service/src/api/routes/search.py

**Checkpoint**: User Story 3 완료 - 키워드 검색 + 필터링 + 정렬 가능

---

## Phase 6: User Story 4 - 무한 스크롤 페이지네이션 (Priority: P2)

**Goal**: 커서 기반 페이지네이션으로 다음 페이지 로드

**Independent Test**: 첫 요청에서 `next_cursor`와 `has_more=true` 반환, 커서로 다음 요청 시 나머지 결과 반환

### Tests for User Story 4

- [X] T036 [P] [US4] Contract test for pagination in services/recipe-service/tests/contract/test_search_pagination.py (첫 페이지, 다음 페이지, 마지막 페이지)
- [X] T037 [P] [US4] Integration test for pagination in services/recipe-service/tests/integration/test_search_pagination.py (커서 연속성 검증)

### Implementation for User Story 4

- [X] T038 [US4] Implement cursor encoding in services/recipe-service/src/utils/cursor.py (base64 JSON: sort, value, id)
- [X] T039 [US4] Implement cursor decoding in services/recipe-service/src/utils/cursor.py (base64 decode, JSON parse)
- [X] T040 [US4] Implement cursor condition for relevance sort in services/recipe-service/src/services/search_service.py (WHERE exposure_score < :prev_score OR ...)
- [X] T041 [US4] Implement cursor conditions for other sorts in services/recipe-service/src/services/search_service.py (latest, cook_time, popularity)
- [X] T042 [US4] Implement has_more detection in services/recipe-service/src/services/search_service.py (fetch limit+1, check if extra exists)
- [X] T043 [US4] Implement next_cursor generation in services/recipe-service/src/services/search_service.py (encode last item's values)
- [X] T044 [US4] Update search endpoint to handle cursor and limit params in services/recipe-service/src/api/routes/search.py
- [X] T045 [US4] Add validation for cursor and limit in services/recipe-service/src/schemas/search.py (cursor max_length=200, limit 1-100)
- [X] T046 [US4] Add error handling for INVALID_CURSOR in services/recipe-service/src/api/routes/search.py

**Checkpoint**: User Story 4 완료 - 무한 스크롤 페이지네이션 가능

---

## Phase 7: User Story 5 - 검색 결과 캐싱 (Priority: P3)

**Goal**: 동일한 검색 조건에 대해 Redis 캐시된 결과 반환 (TTL 5분)

**Independent Test**: 동일 검색 요청 두 번 수행 시 두 번째 요청은 캐시에서 반환 (응답 시간 50ms 이내)

### Tests for User Story 5

- [X] T047 [P] [US5] Contract test for caching in services/recipe-service/tests/contract/test_search_cache.py (캐시 키 생성, 직렬화, TTL 설정 검증)

### Implementation for User Story 5

- [X] T048 [US5] Implement cache key generation in services/recipe-service/src/services/search_service.py (get_search_cache_key: MD5 hash of params)
- [X] T049 [US5] Implement cache get in services/recipe-service/src/services/search_service.py (Redis GET with JSON decode)
- [X] T050 [US5] Implement cache set in services/recipe-service/src/services/search_service.py (Redis SET with TTL 300s)
- [X] T051 [US5] Integrate caching into search flow in services/recipe-service/src/services/search_service.py (check cache before DB query)
- [X] T052 [US5] Add cache config in services/recipe-service/src/core/config.py (SEARCH_CACHE_TTL=300)

**Checkpoint**: User Story 5 완료 - 검색 결과 캐싱으로 성능 최적화

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 전체 기능 마무리 및 품질 개선

- [X] T053 [P] Add structured logging for search operations in services/recipe-service/src/services/search_service.py
- [ ] T054 [P] Add metrics for search latency in services/recipe-service/src/services/search_service.py (Prometheus histogram) - Deferred: 인프라 메트릭 수집 설정 후 추가
- [ ] T055 Run quickstart.md validation scenarios with curl commands - Deferred: 개발 서버 실행 필요
- [ ] T056 Update API documentation in services/recipe-service/docs/ - Deferred: OpenAPI 자동 생성
- [ ] T057 Performance test with hey tool (target: p99 < 200ms, 1000 RPS) - Deferred: 성능 테스트 환경 필요

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1, US2 (P1): Can proceed in parallel after Foundation
  - US3, US4 (P2): Can proceed in parallel after Foundation
  - US5 (P3): Can start after Foundation
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Builds on US1 search infrastructure but independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Adds sorting to existing search
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Adds pagination, integrates with US3 sorting
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - Caching layer on top of complete search

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Validation schemas before service logic
- Service logic before endpoint handlers
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
```bash
Task T002: Create search Pydantic schemas
Task T003: Create cursor encoding utilities
# Can run in parallel - different files
```

**Phase 2 (Foundational)**:
```bash
Task T005: Create search service base
Task T006: Create search router
# Can run in parallel - different files
```

**User Story Tests**:
```bash
# All test tasks for a story can run in parallel
Task T008: Contract test for keyword search
Task T009: Integration test for keyword search
```

**Cross-Story Parallel**:
```bash
# After Foundational phase, different stories can be worked on by different developers
Developer A: User Story 1 (keyword search)
Developer B: User Story 2 (filtering)
```

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T008: "Contract test for keyword search in services/recipe-service/tests/contract/test_search_keyword.py"
Task T009: "Integration test for keyword search in services/recipe-service/tests/integration/test_search_keyword.py"

# After tests fail (as expected), implement in sequence:
Task T010-T016: Sequential implementation of keyword search
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (키워드 검색)
4. **STOP and VALIDATE**: Test `GET /recipes/search?q=김치` independently
5. Deploy/demo if ready - 기본 검색 기능 사용 가능

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! 키워드 검색)
3. Add User Story 2 → Test independently → Deploy/Demo (+ 필터링)
4. Add User Story 3 → Test independently → Deploy/Demo (+ 정렬)
5. Add User Story 4 → Test independently → Deploy/Demo (+ 페이지네이션)
6. Add User Story 5 → Test independently → Deploy/Demo (+ 캐싱)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (keyword search)
   - Developer B: User Story 2 (filtering)
3. After US1 + US2 complete:
   - Developer A: User Story 3 (sorting)
   - Developer B: User Story 4 (pagination)
4. Finally: User Story 5 (caching) + Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution III (TDD): All user stories include test tasks
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
