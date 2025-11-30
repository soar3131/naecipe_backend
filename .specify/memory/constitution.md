<!--
Sync Impact Report
==================
- Version change: 0.0.0 → 1.0.0 (Initial)
- Added principles:
  - I. API-First Design
  - II. Microservice Architecture
  - III. Test-Driven Development (TDD)
  - IV. Event-Driven Integration
  - V. Security by Design
  - VI. Observability & Reliability
  - VII. Simplicity & Pragmatism
- Added sections:
  - Technical Standards
  - Quality Gates
  - Governance
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check section exists)
  - ✅ .specify/templates/spec-template.md (compatible)
  - ✅ .specify/templates/tasks-template.md (compatible)
- Follow-up TODOs: None
-->

# Naecipe Backend Constitution

## Core Principles

### I. API-First Design

모든 서비스 개발은 API 명세를 먼저 정의한 후 구현한다.

- 외부 공개 API는 OpenAPI 3.0 스펙으로 문서화 MUST
- 서비스 간 통신은 gRPC proto 파일로 계약 정의 MUST
- API 버전 관리는 URL 경로(`/v1/`, `/v2/`)로 명시 MUST
- Breaking Change 발생 시 최소 1개 버전 하위 호환 유지 MUST

### II. Microservice Architecture

도메인 경계를 명확히 하고, 서비스 간 결합도를 최소화한다.

- 각 서비스는 독립적으로 배포 가능해야 함 MUST
- 도메인별 데이터베이스 분리 원칙 준수 MUST (Recipe DB, User DB, Cookbook DB 등)
- 서비스 간 동기 통신은 gRPC, 비동기 통신은 Kafka 사용 MUST
- 공유 라이브러리는 `shared/` 패키지로 관리하되, 비즈니스 로직 포함 금지 MUST

### III. Test-Driven Development (TDD)

테스트는 구현의 전제 조건이다.

- Contract 테스트: API 명세 기반 계약 테스트 MUST (OpenAPI/gRPC)
- Integration 테스트: 서비스 간 통신 및 DB 연동 테스트 MUST
- Unit 테스트: 비즈니스 로직 단위 테스트 SHOULD (커버리지 80% 목표)
- E2E 테스트: Core Loop 시나리오 검증 SHOULD
- 테스트 실패 시 CI 파이프라인 중단 MUST

### IV. Event-Driven Integration

서비스 간 상태 변경은 이벤트로 전파한다.

- 도메인 이벤트는 Kafka 토픽으로 발행 MUST
- 이벤트 스키마는 Avro 또는 JSON Schema로 정의 MUST
- Consumer Group 격리로 서비스 독립성 보장 MUST
- 이벤트 재처리를 위한 멱등성 보장 MUST

### V. Security by Design

보안은 설계 단계부터 고려한다.

- OWASP Top 10 취약점 대응 MUST
- 인증/인가는 JWT + Redis 세션 조합 MUST
- 민감 데이터(검색어, 행동 로그)는 암호화 및 비식별화 MUST
- 외부 입력은 Pydantic 모델로 검증 MUST
- SQL Injection 방지를 위해 SQLAlchemy ORM 사용 MUST

### VI. Observability & Reliability

시스템 상태는 항상 관측 가능해야 한다.

- 구조화된 로깅(JSON 포맷) MUST
- 분산 추적(Jaeger/OpenTelemetry) MUST
- 메트릭 수집(Prometheus) 및 대시보드(Grafana) MUST
- Health Check 엔드포인트(`/health`, `/ready`) MUST
- 서비스 응답 시간 SLA: 검색 < 200ms, 상세 < 100ms (p99) MUST

### VII. Simplicity & Pragmatism

복잡성은 명시적 정당화가 필요하다.

- YAGNI 원칙: 현재 필요한 기능만 구현 MUST
- 추상화 레이어는 최소화하고 직접 구현 우선 SHOULD
- 프레임워크/라이브러리 도입 시 근거 문서화 MUST
- 코드 중복이 추상화보다 나은 경우 허용 SHOULD (3회 반복 전까지)

## Technical Standards

### Language & Framework

| 구분 | 기술 | 버전 |
|------|------|------|
| Backend | Python + FastAPI | 3.11+, 0.100+ |
| Database | PostgreSQL + pgvector | 15+ |
| Cache | Redis Cluster | 7+ |
| Message Queue | Apache Kafka | 3.5+ |
| AI Agent | LangGraph + OpenAI/Anthropic | Latest |

### Project Structure

```
services/
├── recipe-service/      # 레시피 CRUD, 검색 (Port 8001)
├── user-service/        # 인증, 사용자 관리 (Port 8002)
├── cookbook-service/    # 레시피북, 피드백 (Port 8003)
├── ai-agent-service/    # LangGraph 기반 AI (Port 8004)
├── embedding-service/   # 벡터 임베딩 (Port 8005)
├── search-service/      # Elasticsearch 연동 (Port 8006)
├── notification-service/# 알림 (Port 8007)
├── analytics-service/   # 이벤트 집계 (Port 8008)
└── ingestion-service/   # 크롤링 레시피 수신 (Port 8009)

shared/
├── proto/               # gRPC 프로토콜 정의
├── schemas/             # 공통 Pydantic 모델
└── utils/               # 공통 유틸리티

specs/                   # Spec-Kit 기능 명세
```

### Coding Standards

- Type Hints 필수 (mypy strict mode)
- Docstring: Google Style
- 함수/메서드 최대 50줄
- 복잡도: Cyclomatic Complexity ≤ 10
- Import 정렬: isort
- 포매팅: Black (line-length: 100)
- 린팅: Ruff

## Quality Gates

### PR Merge 조건

1. 모든 CI 테스트 통과 MUST
2. 코드 리뷰 최소 1인 승인 MUST
3. 보안 취약점 스캔 통과 MUST (Snyk/Dependabot)
4. 커버리지 기준 충족 SHOULD (전체 80%, 신규 코드 90%)

### 배포 조건

1. Staging 환경 E2E 테스트 통과 MUST
2. Performance 벤치마크 SLA 충족 MUST
3. Rollback 계획 문서화 MUST

## Governance

### Constitution 적용

- 본 Constitution은 모든 개발 활동에 우선 적용된다
- PR/코드 리뷰 시 Constitution 준수 여부 확인 MUST
- 위반 사항은 명시적 정당화 없이 Merge 불가

### 개정 절차

1. 개정 제안서 작성 (변경 사유, 영향 범위)
2. 팀 리뷰 및 합의
3. 버전 업데이트 (Semantic Versioning)
4. 관련 템플릿/문서 동기화

### 버전 관리

- MAJOR: 원칙 삭제 또는 비호환 변경
- MINOR: 원칙 추가 또는 확장
- PATCH: 문구 수정, 오타 교정

**Version**: 1.0.0 | **Ratified**: 2025-11-30 | **Last Amended**: 2025-11-30
