# Tasks: 사용자 인증 기본

**Input**: Design documents from `/specs/001-user-auth/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Constitution III조(TDD) 준수를 위해 Contract/Integration 테스트 포함

**Organization**: Tasks are grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Microservice**: `services/user-service/` at repository root
- Source: `services/user-service/src/`
- Tests: `services/user-service/tests/`

---

## Phase 1: Setup (프로젝트 초기화)

**Purpose**: User Service 프로젝트 구조 및 의존성 설정

- [X] T001 Create user-service project structure in services/user-service/ per plan.md
- [X] T002 Initialize pyproject.toml with FastAPI, python-jose, passlib, SQLAlchemy, redis dependencies in services/user-service/pyproject.toml
- [X] T003 [P] Create configuration module with environment variables in services/user-service/src/config.py
- [X] T004 [P] Setup Alembic migration environment in services/user-service/alembic/
- [X] T005 [P] Create Dockerfile for user-service in services/user-service/Dockerfile

---

## Phase 2: Foundational (핵심 인프라)

**Purpose**: 모든 User Story 구현 전 필수 인프라

**⚠️ CRITICAL**: 이 Phase 완료 전까지 User Story 작업 불가

- [X] T006 Implement database session management in services/user-service/src/db/session.py
- [X] T007 [P] Implement Redis client with connection pool in services/user-service/src/db/redis.py
- [X] T008 [P] Create User SQLAlchemy model in services/user-service/src/models/user.py
- [X] T009 Create Alembic migration 001_create_users in services/user-service/alembic/versions/001_create_users.py
- [X] T010 [P] Implement password hashing utilities (bcrypt) in services/user-service/src/core/security.py
- [X] T011 [P] Implement JWT token utilities (create/verify) in services/user-service/src/core/security.py
- [X] T012 [P] Create custom exceptions (RFC 7807 ProblemDetail) in services/user-service/src/core/exceptions.py
- [X] T013 [P] Create Pydantic schemas for auth in services/user-service/src/schemas/auth.py
- [X] T014 [P] Create Pydantic schemas for user in services/user-service/src/schemas/user.py
- [X] T015 Implement token validation dependency in services/user-service/src/api/deps.py
- [X] T016 Setup FastAPI app with CORS, exception handlers in services/user-service/src/main.py
- [X] T017 [P] Create v1 router structure in services/user-service/src/api/v1/__init__.py and router.py
- [X] T018 [P] Setup pytest fixtures for testing in services/user-service/tests/conftest.py
- [X] T019 Implement Health Check endpoints (/health, /ready) in services/user-service/src/main.py

**Checkpoint**: Foundation ready - User Story 구현 가능

---

## Phase 3: User Story 1 - 이메일 회원가입 (Priority: P1) 🎯 MVP

**Goal**: 신규 사용자가 이메일과 비밀번호로 계정을 생성한다

**Independent Test**: 이메일과 비밀번호로 회원가입 요청 시 계정이 생성되고 성공 응답을 받는다

### Tests for User Story 1

- [X] T020 [P] [US1] Contract test for POST /v1/auth/register in services/user-service/tests/contract/test_register.py
- [X] T021 [P] [US1] Integration test for registration flow in services/user-service/tests/integration/test_register.py

### Implementation for User Story 1

- [X] T022 [US1] Implement UserService.create_user() in services/user-service/src/services/user.py
- [X] T023 [US1] Implement POST /v1/auth/register endpoint in services/user-service/src/api/v1/auth.py
- [X] T024 [US1] Add email validation and duplicate check in services/user-service/src/services/user.py
- [X] T025 [US1] Add password policy validation (min 8 chars, alphanumeric) in services/user-service/src/schemas/auth.py

**Checkpoint**: 회원가입 기능 독립적으로 테스트 가능

---

## Phase 4: User Story 2 - 로그인 및 토큰 발급 (Priority: P1)

**Goal**: 등록된 사용자가 로그인하여 Access Token과 Refresh Token을 받는다

**Independent Test**: 올바른 자격 증명으로 로그인하고 토큰으로 보호된 API에 접근할 수 있다

### Tests for User Story 2

- [X] T026 [P] [US2] Contract test for POST /v1/auth/login in services/user-service/tests/contract/test_login.py
- [X] T027 [P] [US2] Contract test for GET /v1/auth/me in services/user-service/tests/contract/test_me.py
- [X] T028 [P] [US2] Integration test for login flow in services/user-service/tests/integration/test_login.py

### Implementation for User Story 2

- [X] T029 [US2] Implement SessionService for Redis session management in services/user-service/src/services/session.py
- [X] T030 [US2] Implement AuthService.login() with token generation in services/user-service/src/services/auth.py
- [X] T031 [US2] Implement POST /v1/auth/login endpoint in services/user-service/src/api/v1/auth.py
- [X] T032 [US2] Implement GET /v1/auth/me endpoint in services/user-service/src/api/v1/auth.py
- [X] T033 [US2] Add login failure counter (Redis) for account lockout in services/user-service/src/services/auth.py
- [X] T034 [US2] Implement account lock check on login in services/user-service/src/services/auth.py

**Checkpoint**: 로그인 및 인증된 API 접근 독립적으로 테스트 가능

---

## Phase 5: User Story 3 - 토큰 갱신 (Priority: P2)

**Goal**: Refresh Token으로 새로운 Access Token을 발급받아 재로그인 없이 서비스 이용

**Independent Test**: Access Token 만료 후 Refresh Token으로 새 토큰을 발급받을 수 있다

### Tests for User Story 3

- [X] T035 [P] [US3] Contract test for POST /v1/auth/refresh in services/user-service/tests/contract/test_refresh.py
- [X] T036 [P] [US3] Integration test for token refresh flow in services/user-service/tests/integration/test_refresh.py

### Implementation for User Story 3

- [X] T037 [US3] Implement AuthService.refresh_token() in services/user-service/src/services/auth.py
- [X] T038 [US3] Implement POST /v1/auth/refresh endpoint in services/user-service/src/api/v1/auth.py
- [X] T039 [US3] Add Refresh Token validation with session check in services/user-service/src/services/auth.py
- [X] T040 [US3] Implement Refresh Token rotation (new token on refresh) in services/user-service/src/services/auth.py

**Checkpoint**: 토큰 갱신 기능 독립적으로 테스트 가능

---

## Phase 6: User Story 4 - 로그아웃 (Priority: P2)

**Goal**: 사용자가 로그아웃하여 토큰을 무효화한다

**Independent Test**: 로그아웃 후 이전 토큰으로 API 접근이 차단된다

### Tests for User Story 4

- [X] T041 [P] [US4] Contract test for POST /v1/auth/logout in services/user-service/tests/contract/test_logout.py
- [X] T042 [P] [US4] Integration test for logout and token invalidation in services/user-service/tests/integration/test_logout.py

### Implementation for User Story 4

- [X] T043 [US4] Implement AuthService.logout() with session deletion in services/user-service/src/services/auth.py
- [X] T044 [US4] Implement Access Token blacklist in Redis in services/user-service/src/services/session.py
- [X] T045 [US4] Implement POST /v1/auth/logout endpoint in services/user-service/src/api/v1/auth.py
- [X] T046 [US4] Add blacklist check to token validation dependency in services/user-service/src/api/deps.py

**Checkpoint**: 로그아웃 및 토큰 무효화 독립적으로 테스트 가능

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 전체 품질 향상 및 통합 검증

- [X] T047 [P] Add structured JSON logging in services/user-service/src/core/logging.py
- [X] T048 [P] Add OpenTelemetry tracing setup in services/user-service/src/core/tracing.py
- [X] T049 [P] Unit tests for security utilities in services/user-service/tests/unit/test_security.py
- [X] T050 [P] Unit tests for auth service in services/user-service/tests/unit/test_auth_service.py
- [X] T051 Run full integration test suite and validate quickstart.md scenarios
- [X] T052 Update services/user-service/README.md with setup and usage instructions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - 즉시 시작 가능
- **Phase 2 (Foundational)**: Phase 1 완료 필수 - **모든 User Story 블로킹**
- **Phase 3-6 (User Stories)**: Phase 2 완료 필수, 이후 병렬 또는 순차 진행 가능
- **Phase 7 (Polish)**: 원하는 User Story 완료 후 진행

### User Story Dependencies

- **US1 (회원가입)**: Phase 2 완료 후 시작 - 다른 스토리 의존 없음
- **US2 (로그인)**: Phase 2 완료 후 시작 - US1과 통합 테스트 시 필요하나 독립 테스트 가능
- **US3 (토큰 갱신)**: Phase 2 완료 후 시작 - US2 로그인 후 토큰 필요하나 독립 테스트 가능
- **US4 (로그아웃)**: Phase 2 완료 후 시작 - US2 로그인 후 토큰 필요하나 독립 테스트 가능

### Within Each User Story

- Tests MUST be written first and FAIL before implementation
- Services before endpoints
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1: T003, T004, T005 병렬 가능
- Phase 2: T007, T008, T010, T011, T012, T013, T014, T017, T018 병렬 가능
- Phase 3 Tests: T020, T021 병렬 가능
- Phase 4 Tests: T026, T027, T028 병렬 가능
- Phase 5 Tests: T035, T036 병렬 가능
- Phase 6 Tests: T041, T042 병렬 가능
- Phase 7: T047, T048, T049, T050 병렬 가능

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all parallel foundational tasks:
Task: "Implement Redis client in src/db/redis.py" [P]
Task: "Create User model in src/models/user.py" [P]
Task: "Implement password hashing in src/core/security.py" [P]
Task: "Implement JWT utilities in src/core/security.py" [P]
Task: "Create custom exceptions in src/core/exceptions.py" [P]
Task: "Create auth schemas in src/schemas/auth.py" [P]
Task: "Create user schemas in src/schemas/user.py" [P]
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 (회원가입)
4. Complete Phase 4: US2 (로그인)
5. **STOP and VALIDATE**: 회원가입 → 로그인 → API 접근 플로우 검증
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (회원가입) → Test → Deploy (가입만 가능)
3. Add US2 (로그인) → Test → Deploy (가입 + 로그인 MVP!)
4. Add US3 (토큰 갱신) → Test → Deploy
5. Add US4 (로그아웃) → Test → Deploy

---

## Summary

| Phase | Tasks | Parallel | Description |
|-------|-------|----------|-------------|
| 1. Setup | 5 | 3 | 프로젝트 초기화 |
| 2. Foundational | 14 | 11 | 핵심 인프라 |
| 3. US1 | 6 | 2 | 회원가입 |
| 4. US2 | 9 | 3 | 로그인 |
| 5. US3 | 6 | 2 | 토큰 갱신 |
| 6. US4 | 6 | 2 | 로그아웃 |
| 7. Polish | 6 | 4 | 품질 향상 |
| **Total** | **52** | **27** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story (US1-US4)
- Constitution III조: TDD 준수 - 테스트 먼저 작성
- Constitution V조: Security - bcrypt, JWT+Redis, Pydantic 검증 적용
- Constitution VII조: Simplicity - SPEC-001 범위 내 최소 구현
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
