# Tasks: 백엔드 프로젝트 기반 설정

**Input**: Design documents from `/specs/001-project-setup/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, contracts/health-api.yaml ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (프로젝트 초기화)

**Purpose**: 모노레포 기본 구조 및 루트 설정

- [x] T001 프로젝트 기본 디렉토리 구조 생성 (services/, shared/, docker/, scripts/)
- [x] T002 루트 pyproject.toml 생성 (workspace 정의, ruff/black/mypy 설정)
- [x] T003 [P] Makefile 생성 (공통 명령어: setup, dev, test, lint, format, infra-up, infra-down)
- [x] T004 [P] .gitignore 생성 (Python, IDE, 환경 파일 제외 패턴)
- [x] T005 [P] .env.example 생성 (환경 변수 템플릿)

---

## Phase 2: Foundational (인프라 및 공통 기반)

**Purpose**: 모든 유저 스토리가 의존하는 핵심 인프라

**⚠️ CRITICAL**: 이 단계 완료 전까지 유저 스토리 작업 불가

- [x] T006 Docker Compose 파일 생성 docker/docker-compose.yml (PostgreSQL, Redis, Elasticsearch, Kafka, Zookeeper)
- [x] T007 [P] shared/proto/ 패키지 생성 (gRPC proto 정의 디렉토리 구조, __init__.py)
- [x] T008 [P] shared/schemas/ 패키지 생성 (공통 Pydantic 스키마 디렉토리 구조, __init__.py)
- [x] T009 [P] shared/utils/ 패키지 생성 (공통 유틸리티 디렉토리 구조, __init__.py)
- [x] T010 shared/pyproject.toml 생성 (shared 패키지 의존성 정의)

**Checkpoint**: 인프라 준비 완료 - 유저 스토리 구현 시작 가능

---

## Phase 3: User Story 1 - 백엔드 개발 환경 구성 (Priority: P1) 🎯 MVP

**Goal**: 신규 개발자가 5분 내에 환경 구성 후 API 서버 시작 가능

**Independent Test**: `make setup && make infra-up && make dev-service SERVICE=recipe-service` 후 `/health` 200 OK

### Implementation for User Story 1

- [x] T011 [US1] scripts/setup.sh 생성 (uv venv, uv sync 자동화)
- [x] T012 [US1] scripts/dev.sh 생성 (단일/전체 서비스 시작 스크립트)
- [x] T013 [US1] 템플릿 서비스 생성 services/recipe-service/pyproject.toml
- [x] T014 [US1] 템플릿 서비스 src 구조 생성 services/recipe-service/src/recipe_service/__init__.py
- [x] T015 [US1] 템플릿 서비스 main.py 생성 services/recipe-service/src/recipe_service/main.py (FastAPI 앱)
- [x] T016 [US1] 템플릿 서비스 config.py 생성 services/recipe-service/src/recipe_service/core/config.py (Pydantic Settings)
- [x] T017 [US1] 템플릿 서비스 health.py 생성 services/recipe-service/src/recipe_service/api/health.py (/health, /ready 엔드포인트)
- [x] T018 [US1] 템플릿 서비스 Dockerfile 생성 services/recipe-service/Dockerfile
- [x] T019 [US1] 템플릿 서비스 tests/conftest.py 생성

**Checkpoint**: recipe-service 단독 실행 및 헬스체크 확인 가능

---

## Phase 4: User Story 2 - 개별 마이크로서비스 개발 (Priority: P2)

**Goal**: 9개 마이크로서비스 독립 실행 환경 구축

**Independent Test**: 각 서비스별 `uvicorn src.[service_name].main:app --reload --port [PORT]` 실행 가능

### Implementation for User Story 2

모든 서비스는 recipe-service 템플릿을 기반으로 생성 (병렬 가능)

- [x] T020 [P] [US2] services/user-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T021 [P] [US2] services/cookbook-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T022 [P] [US2] services/ai-agent-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T023 [P] [US2] services/embedding-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T024 [P] [US2] services/search-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T025 [P] [US2] services/notification-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T026 [P] [US2] services/analytics-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)
- [x] T027 [P] [US2] services/ingestion-service/ 구조 생성 (pyproject.toml, src/, Dockerfile)

**Checkpoint**: 모든 9개 서비스 독립 실행 가능

---

## Phase 5: User Story 3 - 공통 패키지 활용 (Priority: P3)

**Goal**: 서비스 간 공유 코드 패키지 구현

**Independent Test**: `from shared.schemas import BaseResponse` 가 두 개 이상 서비스에서 정상 동작

### Implementation for User Story 3

- [x] T028 [P] [US3] shared/schemas/base.py 생성 (공통 Response 스키마: BaseResponse, ErrorResponse)
- [x] T029 [P] [US3] shared/schemas/health.py 생성 (HealthResponse, ReadinessResponse 스키마)
- [x] T030 [P] [US3] shared/utils/logging.py 생성 (structlog 설정 함수)
- [x] T031 [US3] recipe-service에서 shared 패키지 import 확인 및 적용

**Checkpoint**: shared 패키지가 recipe-service에서 정상 import

---

## Phase 6: User Story 4 - 데이터베이스 스키마 관리 (Priority: P4)

**Goal**: Alembic 마이그레이션 인프라 구축

**Independent Test**: `alembic revision --autogenerate -m "test"` → `alembic upgrade head` → `alembic downgrade -1` 성공

### Implementation for User Story 4

- [x] T032 [US4] recipe-service Alembic 초기화 services/recipe-service/alembic.ini
- [x] T033 [US4] recipe-service alembic/env.py 생성 (async SQLAlchemy 설정)
- [x] T034 [US4] recipe-service alembic/versions/ 디렉토리 생성
- [x] T035 [US4] Makefile에 migrate, migrate-create, migrate-rollback 명령어 추가
- [x] T036 [US4] 샘플 모델 생성 services/recipe-service/src/recipe_service/models/base.py (SQLAlchemy Base)

**Checkpoint**: recipe-service에서 마이그레이션 생성/적용/롤백 가능

---

## Phase 7: User Story 5 - 환경별 설정 관리 (Priority: P5)

**Goal**: Pydantic Settings 기반 환경 변수 관리 체계 구축

**Independent Test**: 필수 환경 변수 누락 시 ValidationError 발생, 민감 정보 로그 마스킹

### Implementation for User Story 5

- [x] T037 [US5] shared/utils/settings.py 생성 (공통 BaseSettings 클래스, SecretStr 활용)
- [x] T038 [US5] recipe-service config.py 업데이트 (DatabaseSettings, RedisSettings, KafkaSettings 분리)
- [x] T039 [US5] 환경 변수 검증 로직 추가 (필수 변수 누락 시 명확한 오류 메시지)
- [x] T040 [US5] structlog 설정에 민감 정보 마스킹 프로세서 추가

**Checkpoint**: 환경 변수 검증 및 마스킹 동작 확인

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 전체 프로젝트 품질 향상

- [x] T041 [P] README.md 업데이트 (프로젝트 소개, 퀵스타트 링크)
- [x] T042 [P] pre-commit 설정 .pre-commit-config.yaml (ruff, black, mypy)
- [x] T043 [P] GitHub Actions CI 워크플로우 .github/workflows/ci.yml (lint, test)
- [ ] T044 quickstart.md 검증 실행 (실제 환경에서 단계별 테스트)
- [ ] T045 전체 서비스 동시 실행 테스트 (8GB 메모리 내 동작 확인)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ──────────────────────────────────────────────┐
    │                                                        │
    ▼                                                        │
Phase 2: Foundational ◄── BLOCKS ALL USER STORIES ───────────┤
    │                                                        │
    ├─────────────┬─────────────┬─────────────┬─────────────┤
    ▼             ▼             ▼             ▼             ▼
Phase 3: US1   Phase 4: US2  Phase 5: US3  Phase 6: US4  Phase 7: US5
(P1 MVP)       (P2)          (P3)          (P4)          (P5)
    │             │             │             │             │
    └─────────────┴─────────────┴─────────────┴─────────────┘
                                │
                                ▼
                        Phase 8: Polish
```

### User Story Dependencies

| Story | 선행 조건 | 병렬 가능 여부 |
|-------|----------|--------------|
| US1 (P1) | Phase 2 완료 | 단독 진행 (MVP) |
| US2 (P2) | Phase 3 완료 (템플릿 필요) | US3, US4, US5와 병렬 |
| US3 (P3) | Phase 2 완료 | US2, US4, US5와 병렬 |
| US4 (P4) | Phase 3 완료 (서비스 필요) | US2, US3, US5와 병렬 |
| US5 (P5) | Phase 3 완료 (서비스 필요) | US2, US3, US4와 병렬 |

### Parallel Opportunities

```bash
# Phase 1: Setup 내 병렬 실행 가능
Task: T003 Makefile 생성
Task: T004 .gitignore 생성
Task: T005 .env.example 생성

# Phase 2: Foundational 내 병렬 실행 가능
Task: T007 shared/proto/ 패키지 생성
Task: T008 shared/schemas/ 패키지 생성
Task: T009 shared/utils/ 패키지 생성

# Phase 4: US2 전체 서비스 병렬 생성
Task: T020 ~ T027 (8개 서비스 동시 생성)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup 완료
2. Phase 2: Foundational 완료
3. Phase 3: User Story 1 완료
4. **STOP and VALIDATE**: recipe-service 단독 실행 및 `/health` 확인
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → 인프라 준비 완료
2. User Story 1 → 템플릿 서비스 완성 (MVP!)
3. User Story 2 → 9개 서비스 구조 완성
4. User Story 3 → 공통 패키지 활용 가능
5. User Story 4 → DB 마이그레이션 가능
6. User Story 5 → 환경 설정 체계 완성
7. Polish → CI/CD, 문서화 완성

---

## Notes

- [P] 태스크 = 다른 파일 대상, 의존성 없음
- [US#] 라벨 = 해당 유저 스토리 매핑
- 각 유저 스토리는 독립적으로 완료/테스트 가능
- 체크포인트에서 중단하고 스토리 독립 검증 권장
- 태스크 완료 후 커밋 권장
