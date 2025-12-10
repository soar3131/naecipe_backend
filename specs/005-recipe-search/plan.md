# Implementation Plan: 원본 레시피 검색

**Branch**: `005-recipe-search` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-recipe-search/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

원본 레시피 검색 기능 구현 - 키워드 검색, 다중 필터링, 정렬, 커서 기반 페이지네이션을 지원하는 검색 API를 recipe-service에 구현합니다.

**Phase 1 MVP 기술 접근**:
- PostgreSQL ILIKE 기반 부분 일치 검색 (제목, 설명, 재료명, 요리사명)
- 동적 쿼리 빌더 (SQLAlchemy) 를 통한 필터 조합
- 커서 기반 페이지네이션 (keyset pagination)
- Redis 캐싱 (쿼리 해시 키, TTL 5분)
- 성능 목표: p99 < 200ms, 1000 RPS

## Technical Context

<!--
  내시피(Naecipe) 백엔드 프로젝트 기본 설정
  Constitution에 정의된 기술 스택을 기준으로 합니다.
-->

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy, Pydantic, LangGraph
**Storage**: PostgreSQL 15+ (pgvector), Redis Cluster 7+, Elasticsearch
**Message Queue**: Apache Kafka 3.5+
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux (AWS EKS)
**Project Type**: microservices (services/ 디렉토리 기반)
**Performance Goals**: 검색 < 200ms, 상세 < 100ms (p99), AI 보정 < 10초
**Constraints**: 가용성 99.9%, 동시 사용자 50,000명
**Scale/Scope**: 9개 마이크로서비스, Phase 1 MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ `contracts/openapi.yaml` 완성 |
| II. Microservice | 도메인 경계 명확함? 독립 배포 가능? | ✅ recipe-service에 검색 기능 추가, 기존 DB 재사용 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ spec.md에 Acceptance Scenarios 정의됨 |
| IV. Event-Driven | Kafka 이벤트 스키마 정의됨? | ⬜ 검색 기능은 이벤트 발행 없음 (조회 전용) |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ Pydantic 검증, SQLAlchemy 파라미터 바인딩 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ 기존 recipe-service 인프라 재사용 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ PostgreSQL ILIKE로 단순 구현, Phase 2에서 ES 확장 |

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

내시피 백엔드는 마이크로서비스 구조를 따릅니다:

```text
services/
├── [service-name]/          # 개별 마이크로서비스
│   ├── src/
│   │   ├── api/             # FastAPI 라우터
│   │   ├── models/          # SQLAlchemy 모델
│   │   ├── schemas/         # Pydantic 스키마
│   │   ├── services/        # 비즈니스 로직
│   │   └── events/          # Kafka 이벤트 핸들러
│   ├── tests/
│   │   ├── contract/        # API 계약 테스트
│   │   ├── integration/     # 통합 테스트
│   │   └── unit/            # 단위 테스트
│   ├── Dockerfile
│   └── pyproject.toml
│
shared/
├── proto/                   # gRPC 프로토콜 정의
├── schemas/                 # 공통 Pydantic 모델
└── utils/                   # 공통 유틸리티

specs/                       # Spec-Kit 기능 명세
```

**서비스 목록** (Constitution 참조):
- recipe-service (8001), user-service (8002), cookbook-service (8003)
- ai-agent-service (8004), embedding-service (8005), search-service (8006)
- notification-service (8007), analytics-service (8008), ingestion-service (8009)

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
