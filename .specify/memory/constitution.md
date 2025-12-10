<!--
Sync Impact Report
==================
- Version change: 1.0.0 → 2.0.0 (Modular Monolith)
- Modified principles:
  - II. Microservice Architecture → Modular Monolith Architecture
  - IV. Event-Driven Integration → 직접 함수 호출 + BackgroundTasks
  - VI. Observability: Prometheus/Grafana → CloudWatch
- Architecture changes:
  - 9개 독립 서비스 → 1개 앱 + 9개 도메인 모듈
  - 5개 PostgreSQL → 1개 PostgreSQL (스키마 분리)
  - gRPC + Kafka → Python 함수 호출 + BackgroundTasks
  - EKS → ECS Fargate
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md (Constitution Check section exists)
  - ✅ .specify/templates/spec-template.md (compatible)
  - ✅ .specify/templates/tasks-template.md (compatible)
- Follow-up TODOs: None
-->

# Naecipe Backend Constitution

## Core Principles

### I. API-First Design

모든 모듈 개발은 API 명세를 먼저 정의한 후 구현한다.

- 외부 공개 API는 OpenAPI 3.0 스펙으로 문서화 MUST
- ~~서비스 간 통신은 gRPC proto 파일로 계약 정의 MUST~~ → 모듈 간 통신은 Python 함수 호출
- API 버전 관리는 URL 경로(`/v1/`, `/v2/`)로 명시 MUST
- Breaking Change 발생 시 최소 1개 버전 하위 호환 유지 MUST

### II. Modular Monolith Architecture

도메인 경계를 명확히 하고, 모듈 간 결합도를 최소화한다.

- 각 모듈은 명확한 도메인 경계를 가지며, 독립적으로 테스트 가능해야 함 MUST
- ~~도메인별 데이터베이스 분리~~ → 단일 PostgreSQL + 스키마 분리 (recipes, users, cookbooks, knowledge) MUST
- 모듈 간 통신은 Python 함수 호출, 비동기 작업은 BackgroundTasks 사용 MUST
- 공유 레이어(`core/`, `infra/`)는 비즈니스 로직 포함 금지 MUST
- DAU 10만+, 팀 10명+ 시 마이크로서비스 분리 검토 SHOULD

### III. Test-Driven Development (TDD)

테스트는 구현의 전제 조건이다.

- Contract 테스트: API 명세 기반 계약 테스트 MUST (OpenAPI)
- Integration 테스트: 모듈 간 통신 및 DB 연동 테스트 MUST
- Unit 테스트: 비즈니스 로직 단위 테스트 SHOULD (커버리지 80% 목표)
- E2E 테스트: Core Loop 시나리오 검증 SHOULD
- 테스트 실패 시 CI 파이프라인 중단 MUST

### IV. Async Task Processing

비동기 작업은 FastAPI BackgroundTasks로 처리한다.

- ~~도메인 이벤트는 Kafka 토픽으로 발행 MUST~~ → BackgroundTasks로 비동기 처리
- 이메일 발송, AI 처리, 분석 집계 등 비동기 작업에 사용 MUST
- 대용량/내구성 필요 시 SQS 사용 검토 SHOULD
- 비동기 작업 실패 시 로깅 및 재시도 로직 구현 MUST
- DAU 10만+ 시 Kafka 도입 검토 SHOULD

### V. Security by Design

보안은 설계 단계부터 고려한다.

- OWASP Top 10 취약점 대응 MUST
- 인증/인가는 JWT + Redis 세션 조합 MUST
- 민감 데이터(검색어, 행동 로그)는 암호화 및 비식별화 MUST
- 외부 입력은 Pydantic 모델로 검증 MUST
- SQL Injection 방지를 위해 SQLAlchemy ORM 사용 MUST

### VI. Observability & Reliability

시스템 상태는 항상 관측 가능해야 한다.

- 구조화된 로깅(JSON 포맷) MUST → CloudWatch Logs
- ~~분산 추적(Jaeger/OpenTelemetry)~~ → AWS X-Ray (필요시) SHOULD
- ~~메트릭 수집(Prometheus) 및 대시보드(Grafana)~~ → CloudWatch Metrics MUST
- Health Check 엔드포인트(`/health`, `/ready`) MUST
- 앱 응답 시간 SLA: 검색 < 200ms, 상세 < 100ms (p99) MUST

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
| Database | PostgreSQL + pgvector | 15+ (단일 인스턴스, 스키마 분리) |
| Cache | Redis | 7+ (단일 인스턴스) |
| ~~Message Queue~~ | ~~Apache Kafka~~ | → BackgroundTasks (필요시 SQS) |
| AI Agent | LangGraph + OpenAI/Anthropic | Latest |
| Infrastructure | AWS ECS Fargate | 단일 컨테이너 |

### Project Structure

```
app/                     # 단일 FastAPI 앱
├── core/               # 공유 설정, 보안, 의존성
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
├── infra/              # 인프라 레이어 (DB, Redis, S3)
│   ├── database.py
│   ├── redis.py
│   └── s3.py
├── recipes/            # 레시피 도메인 모듈
│   ├── models.py
│   ├── schemas.py
│   ├── services.py
│   └── router.py
├── users/              # 사용자 도메인 모듈
├── cookbooks/          # 레시피북/피드백 모듈
├── ai_agent/           # AI 보정 모듈
├── knowledge/          # 임베딩/검색 모듈
├── notifications/      # 알림 모듈
├── analytics/          # 분석 모듈
├── ingestion/          # 크롤링 수신 모듈
└── main.py             # FastAPI 앱 진입점

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

**Version**: 2.0.0 | **Ratified**: 2025-11-30 | **Last Amended**: 2025-12-10

---

## Version History

| 버전 | 날짜 | 변경 내용 |
|-----|------|----------|
| v1.0.0 | 2025-11-30 | 초기 버전 (마이크로서비스 아키텍처) |
| v2.0.0 | 2025-12-10 | 모듈러 모놀리스 전환, Kafka→BackgroundTasks, EKS→ECS |
