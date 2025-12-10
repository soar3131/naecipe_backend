# Implementation Plan: 백엔드 프로젝트 기반 설정

**Branch**: `001-project-setup` | **Date**: 2025-11-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-project-setup/spec.md`

## Summary

내시피(Naecipe) 백엔드 마이크로서비스 프로젝트의 기반 구조를 설정한다. Python 3.11 + FastAPI 기반의 9개 마이크로서비스를 모노레포로 관리하며, Docker Compose로 로컬 인프라(PostgreSQL, Redis, Elasticsearch, Kafka)를 제공한다. 개발자가 5분 내에 환경을 구성하고 API 개발을 시작할 수 있도록 한다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+, Alembic
**Storage**: PostgreSQL 15+ (pgvector), Redis 7+, Elasticsearch 8+
**Message Queue**: Apache Kafka 3.5+
**Testing**: pytest, pytest-asyncio, pytest-cov
**Target Platform**: Linux (AWS EKS), macOS/Windows (개발)
**Project Type**: microservices 모노레포 (services/ 디렉토리 기반)
**Performance Goals**: 서비스 시작 30초 이내, 핫 리로드 3초 이내
**Constraints**: 전체 서비스 + 인프라 8GB RAM 이내
**Scale/Scope**: 9개 마이크로서비스, Phase 0 프로젝트 설정

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 검증 항목 | 상태 | 비고 |
|------|----------|------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ | `/health`, `/ready` 엔드포인트 OpenAPI 명세 포함 |
| II. Microservice | 도메인 경계 명확함? 독립 배포 가능? | ✅ | 9개 서비스 독립 디렉토리, 개별 pyproject.toml |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ | tests/contract/, tests/integration/ 구조 |
| IV. Event-Driven | Kafka 이벤트 스키마 정의됨? | ⬜ N/A | 프로젝트 설정 단계, 이벤트 스키마는 후속 스펙에서 정의 |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ | Pydantic Settings로 환경 변수 검증, 민감 정보 마스킹 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ | 구조화 로깅, `/health`, `/ready` 엔드포인트 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ | 표준 FastAPI 프로젝트 구조, 최소 의존성 |

## Project Structure

### Documentation (this feature)

```text
specs/001-project-setup/
├── plan.md              # 이 파일
├── research.md          # Phase 0: 기술 결정
├── data-model.md        # Phase 1: 데이터 모델 (해당 없음)
├── quickstart.md        # Phase 1: 빠른 시작 가이드
├── contracts/           # Phase 1: API 명세
│   └── health-api.yaml  # 헬스체크 API OpenAPI 스펙
└── tasks.md             # Phase 2: 태스크 목록
```

### Source Code (repository root)

```text
/
├── services/                    # 마이크로서비스 디렉토리
│   ├── recipe-service/          # 레시피 CRUD (8001)
│   ├── user-service/            # 인증/사용자 (8002)
│   ├── cookbook-service/        # 레시피북 (8003)
│   ├── ai-agent-service/        # AI 에이전트 (8004)
│   ├── embedding-service/       # 벡터 임베딩 (8005)
│   ├── search-service/          # 검색 (8006)
│   ├── notification-service/    # 알림 (8007)
│   ├── analytics-service/       # 분석 (8008)
│   └── ingestion-service/       # 수집 (8009)
│
├── shared/                      # 공통 패키지
│   ├── proto/                   # gRPC 프로토콜 정의
│   ├── schemas/                 # 공통 Pydantic 스키마
│   └── utils/                   # 공통 유틸리티
│
├── docker/                      # Docker 관련 파일
│   └── docker-compose.yml       # 로컬 인프라
│
├── scripts/                     # 개발 스크립트
│   ├── setup.sh                 # 환경 설정
│   └── dev.sh                   # 개발 서버 시작
│
├── .env.example                 # 환경 변수 템플릿
├── pyproject.toml               # 루트 프로젝트 설정
└── Makefile                     # 공통 명령어
```

### 서비스별 디렉토리 구조

```text
services/[service-name]/
├── src/
│   └── [service_name]/          # Python 패키지
│       ├── __init__.py
│       ├── main.py              # FastAPI 앱 엔트리포인트
│       ├── api/                 # API 라우터
│       │   ├── __init__.py
│       │   └── health.py        # 헬스체크 엔드포인트
│       ├── core/                # 설정, 의존성
│       │   ├── __init__.py
│       │   ├── config.py        # Pydantic Settings
│       │   └── deps.py          # 의존성 주입
│       ├── models/              # SQLAlchemy 모델 (필요시)
│       ├── schemas/             # Pydantic 스키마 (필요시)
│       └── services/            # 비즈니스 로직 (필요시)
├── tests/
│   ├── conftest.py              # pytest 설정
│   ├── contract/                # API 계약 테스트
│   ├── integration/             # 통합 테스트
│   └── unit/                    # 단위 테스트
├── alembic/                     # DB 마이그레이션 (필요시)
│   ├── versions/
│   └── env.py
├── alembic.ini
├── Dockerfile
└── pyproject.toml
```

## Complexity Tracking

> 본 스펙에서 Constitution 위반 사항 없음

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| - | - | - |
