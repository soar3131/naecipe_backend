# Tasks: 레시피북 기본 CRUD

**Input**: Design documents from `/specs/007-cookbook-basic-crud/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: 태스크는 User Story별로 그룹화되어 독립적 구현 및 테스트가 가능합니다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 병렬 실행 가능 (다른 파일, 의존성 없음)
- **[Story]**: 해당 User Story (US1, US2, US3, US4, US5, US6)
- 정확한 파일 경로 포함

---

## Phase 1: Setup (프로젝트 초기화)

**Purpose**: cookbooks 모듈 기본 구조 및 마이그레이션 설정

- [ ] T001 Create Alembic migration for cookbooks table in alembic/versions/xxx_create_cookbooks_table.py
- [ ] T002 [P] Create Cookbook model in app/cookbooks/models.py
- [ ] T003 [P] Create Pydantic schemas in app/cookbooks/schemas.py
- [ ] T004 [P] Create test fixtures in tests/cookbooks/conftest.py
- [ ] T005 [P] Create tests/cookbooks/__init__.py

**Checkpoint**: cookbooks 모듈 기본 구조 완료 - 모델, 스키마, 테스트 픽스처 준비됨

---

## Phase 2: Foundational (기반 인프라)

**Purpose**: 모든 User Story가 의존하는 핵심 서비스 인프라

**⚠️ CRITICAL**: 이 단계가 완료되어야 User Story 구현 시작 가능

- [ ] T006 Create CookbookService class skeleton in app/cookbooks/services.py
- [ ] T007 Implement ensure_default_cookbook() in app/cookbooks/services.py (Lazy Creation)
- [ ] T008 Create FastAPI router skeleton in app/cookbooks/router.py
- [ ] T009 Register cookbooks router in app/main.py
- [ ] T010 [P] Create custom exceptions in app/cookbooks/exceptions.py

**Checkpoint**: 서비스 기반 완료 - User Story 구현 시작 가능

---

## Phase 3: User Story 1 & 2 - 레시피북 생성 및 목록 조회 (Priority: P1) 🎯 MVP

**Goal**: 레시피북 생성 및 목록 조회로 핵심 CRUD 기능 제공

**Independent Test**: `POST /api/v1/cookbooks`, `GET /api/v1/cookbooks` 호출로 생성/조회 확인

### Tests for User Story 1 & 2

- [ ] T011 [P] [US1] Integration test for create cookbook in tests/cookbooks/test_cookbook_crud.py
- [ ] T012 [P] [US2] Integration test for list cookbooks in tests/cookbooks/test_cookbook_crud.py
- [ ] T013 [P] [US1] Service unit test for create_cookbook in tests/cookbooks/test_cookbook_service.py
- [ ] T014 [P] [US2] Service unit test for get_cookbooks in tests/cookbooks/test_cookbook_service.py

### Implementation for User Story 1 & 2

- [ ] T015 [US1] Implement create_cookbook() in app/cookbooks/services.py
- [ ] T016 [US2] Implement get_cookbooks() with saved_recipe_count subquery in app/cookbooks/services.py
- [ ] T017 [US1] Implement POST /cookbooks endpoint in app/cookbooks/router.py
- [ ] T018 [US2] Implement GET /cookbooks endpoint in app/cookbooks/router.py
- [ ] T019 [US1] Add validation for name length (1-100 chars) in app/cookbooks/schemas.py
- [ ] T020 [US2] Add sort_order ordering in get_cookbooks service

**Checkpoint**: MVP 완료 - 레시피북 생성 및 목록 조회 동작 확인

---

## Phase 4: User Story 3 & 4 - 상세 조회 및 수정 (Priority: P2)

**Goal**: 레시피북 상세 정보 조회 및 수정 기능 제공

**Independent Test**: `GET /api/v1/cookbooks/{id}`, `PUT /api/v1/cookbooks/{id}` 호출로 조회/수정 확인

### Tests for User Story 3 & 4

- [ ] T021 [P] [US3] Integration test for get cookbook detail in tests/cookbooks/test_cookbook_crud.py
- [ ] T022 [P] [US4] Integration test for update cookbook in tests/cookbooks/test_cookbook_crud.py
- [ ] T023 [P] [US3] Service unit test for get_cookbook_by_id in tests/cookbooks/test_cookbook_service.py
- [ ] T024 [P] [US4] Service unit test for update_cookbook in tests/cookbooks/test_cookbook_service.py

### Implementation for User Story 3 & 4

- [ ] T025 [US3] Implement get_cookbook_by_id() in app/cookbooks/services.py
- [ ] T026 [US4] Implement update_cookbook() in app/cookbooks/services.py
- [ ] T027 [US3] Implement GET /cookbooks/{id} endpoint in app/cookbooks/router.py
- [ ] T028 [US4] Implement PUT /cookbooks/{id} endpoint in app/cookbooks/router.py
- [ ] T029 [US4] Add CookbookUpdateRequest schema in app/cookbooks/schemas.py

**Checkpoint**: 상세 조회 및 수정 완료 - 전체 조회/수정 흐름 동작 확인

---

## Phase 5: User Story 5 & 6 - 삭제 및 순서 변경 (Priority: P3)

**Goal**: 레시피북 삭제 및 순서 변경으로 관리 기능 완성

**Independent Test**: `DELETE /api/v1/cookbooks/{id}`, `PATCH /api/v1/cookbooks/reorder` 호출로 삭제/순서변경 확인

### Tests for User Story 5 & 6

- [ ] T030 [P] [US5] Integration test for delete cookbook in tests/cookbooks/test_cookbook_crud.py
- [ ] T031 [P] [US6] Integration test for reorder cookbooks in tests/cookbooks/test_cookbook_crud.py
- [ ] T032 [P] [US5] Service unit test for delete_cookbook in tests/cookbooks/test_cookbook_service.py
- [ ] T033 [P] [US6] Service unit test for reorder_cookbooks in tests/cookbooks/test_cookbook_service.py

### Implementation for User Story 5 & 6

- [ ] T034 [US5] Implement delete_cookbook() with default cookbook check in app/cookbooks/services.py
- [ ] T035 [US6] Implement reorder_cookbooks() with 1-based reassignment in app/cookbooks/services.py
- [ ] T036 [US5] Implement DELETE /cookbooks/{id} endpoint in app/cookbooks/router.py
- [ ] T037 [US6] Implement PATCH /cookbooks/reorder endpoint in app/cookbooks/router.py
- [ ] T038 [US6] Add CookbookReorderRequest schema in app/cookbooks/schemas.py

**Checkpoint**: 삭제 및 순서 변경 완료 - 전체 CRUD 기능 동작 확인

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 품질 개선 및 공통 관심사 처리

- [ ] T039 Add structured logging for all cookbook operations in app/cookbooks/services.py
- [ ] T040 Add OpenAPI documentation comments in app/cookbooks/router.py
- [ ] T041 [P] Run and verify all tests with pytest tests/cookbooks/ -v
- [ ] T042 [P] Verify quickstart.md scenarios manually
- [ ] T043 Performance test: Verify API response time < 200ms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - 즉시 시작 가능
- **Foundational (Phase 2)**: Setup 완료 필요 - 모든 User Story 블로킹
- **User Stories (Phase 3-5)**: Foundational 완료 필요
  - P1 (US1, US2) → P2 (US3, US4) → P3 (US5, US6) 순서 권장
  - 필요시 병렬 진행 가능
- **Polish (Phase 6)**: 모든 User Story 완료 필요

### User Story Dependencies

- **User Story 1 (생성)**: Foundational 완료 후 시작 가능 - 다른 Story 의존 없음
- **User Story 2 (목록)**: Foundational 완료 후 시작 가능 - US1과 병렬 가능
- **User Story 3 (상세)**: US1/US2 완료 권장 - 레시피북 존재 필요
- **User Story 4 (수정)**: US1/US2 완료 권장 - 레시피북 존재 필요
- **User Story 5 (삭제)**: US1/US2 완료 권장 - 레시피북 존재 필요
- **User Story 6 (순서변경)**: US1/US2 완료 권장 - 다수 레시피북 필요

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Services before endpoints
- Core implementation before integration
- Story 완료 후 다음 우선순위로 이동

### Parallel Opportunities

**Setup Phase**:
```
T002, T003, T004, T005 (병렬 실행 가능)
```

**Foundational Phase**:
```
T010 (병렬 실행 가능 - exceptions.py 독립)
```

**User Story 1 & 2 Tests**:
```
T011, T012, T013, T014 (모든 테스트 병렬 작성)
```

**User Story 3 & 4 Tests**:
```
T021, T022, T023, T024 (모든 테스트 병렬 작성)
```

**User Story 5 & 6 Tests**:
```
T030, T031, T032, T033 (모든 테스트 병렬 작성)
```

---

## Implementation Strategy

### MVP First (User Story 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 & 2
4. **STOP and VALIDATE**: 레시피북 생성/목록 조회 테스트
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → 기반 완료
2. Add US1 & US2 → MVP 완료 → Deploy/Demo
3. Add US3 & US4 → 상세/수정 → Deploy/Demo
4. Add US5 & US6 → 삭제/순서 → Deploy/Demo
5. Polish → 최종 품질 개선

### Single Developer Strategy

```
Phase 1 (Setup)       → ~30분
Phase 2 (Foundational) → ~1시간
Phase 3 (US1 & US2)   → ~2시간
Phase 4 (US3 & US4)   → ~1.5시간
Phase 5 (US5 & US6)   → ~1.5시간
Phase 6 (Polish)      → ~30분
                       ────────
Total                  ~7시간
```

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 43 |
| **Setup Tasks** | 5 |
| **Foundational Tasks** | 5 |
| **User Story Tasks** | 28 (US1&2: 10, US3&4: 9, US5&6: 9) |
| **Polish Tasks** | 5 |
| **Parallel Opportunities** | 20+ |

### MVP Scope (Recommended)

- Phase 1 + Phase 2 + Phase 3 (T001-T020)
- 레시피북 생성 및 목록 조회 기능
- 20개 태스크로 핵심 기능 완료

---

## Notes

- [P] tasks = 다른 파일, 의존성 없음 → 병렬 실행 가능
- [Story] label = User Story 추적성
- 각 User Story는 독립적으로 완료 및 테스트 가능
- 테스트가 실패한 후 구현 진행
- 태스크 또는 논리적 그룹 완료 후 커밋
- 각 체크포인트에서 Story 독립 검증 가능

---

**Generated by**: `/speckit.tasks`
**Date**: 2025-12-11
