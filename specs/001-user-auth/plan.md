# Implementation Plan: 사용자 인증 기본

**Branch**: `001-user-auth` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-user-auth/spec.md`

## Summary

이메일/비밀번호 기반 사용자 인증 시스템을 구현합니다. JWT (Access + Refresh Token) 발급, bcrypt 비밀번호 해싱, Redis 세션 관리, 계정 잠금 기능을 포함합니다. User Service (포트 8002)에 구현되며, 다른 모든 서비스의 인증 기반이 됩니다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, python-jose, passlib[bcrypt], SQLAlchemy 2.0+, Pydantic 2.0+
**Storage**: PostgreSQL 15+ (users 테이블), Redis 7+ (세션/블랙리스트)
**Message Queue**: N/A (인증은 동기 처리)
**Testing**: pytest, pytest-asyncio, httpx, fakeredis
**Target Platform**: Linux (AWS EKS)
**Project Type**: microservices (services/user-service)
**Performance Goals**: 로그인 < 100ms, 토큰 검증 < 10ms (p99)
**Constraints**: 가용성 99.9%, 동시 사용자 50,000명
**Scale/Scope**: User Service 단독, SPEC-001 범위 내

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 3.0 스펙 정의 (contracts/openapi.yaml) | ✅ |
| II. Microservice | user-service 독립 서비스, User DB 분리 | ✅ |
| III. TDD | Contract/Integration 테스트 계획 | ✅ |
| IV. Event-Driven | 인증은 동기 처리, 이벤트 불필요 | N/A |
| V. Security | bcrypt, JWT+Redis, Pydantic 검증, 계정 잠금 | ✅ |
| VI. Observability | JSON 로깅, Health Check, 메트릭 계획 | ✅ |
| VII. Simplicity | SPEC-001 범위 내, 최소 추상화 | ✅ |

## Project Structure

### Documentation (this feature)

```text
specs/001-user-auth/
├── spec.md              # 기능 명세
├── plan.md              # 이 파일 (구현 계획)
├── research.md          # 기술 결정 및 근거
├── data-model.md        # 엔티티 및 관계
├── quickstart.md        # 통합 시나리오
├── contracts/
│   └── openapi.yaml     # OpenAPI 3.0 명세
├── checklists/
│   └── requirements.md  # 요구사항 품질 체크리스트
└── tasks.md             # 태스크 목록 (/speckit.tasks 생성)
```

### Source Code (repository root)

```text
services/user-service/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 엔트리포인트
│   ├── config.py               # 환경 설정
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # v1 라우터 통합
│   │   │   └── auth.py         # 인증 엔드포인트
│   │   └── deps.py             # 의존성 주입
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # User SQLAlchemy 모델
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py             # 인증 관련 Pydantic 스키마
│   │   └── user.py             # 사용자 관련 스키마
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py             # 인증 비즈니스 로직
│   │   └── user.py             # 사용자 CRUD 로직
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, 비밀번호 해싱
│   │   └── exceptions.py       # 커스텀 예외
│   └── db/
│       ├── __init__.py
│       ├── session.py          # DB 세션 관리
│       └── redis.py            # Redis 클라이언트
├── tests/
│   ├── conftest.py             # pytest fixtures
│   ├── contract/
│   │   └── test_auth_api.py    # OpenAPI 계약 테스트
│   ├── integration/
│   │   ├── test_auth_flow.py   # 인증 플로우 테스트
│   │   └── test_session.py     # 세션 관리 테스트
│   └── unit/
│       ├── test_security.py    # 보안 유틸 테스트
│       └── test_auth_service.py
├── alembic/
│   ├── versions/
│   │   └── 001_create_users.py
│   └── env.py
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Key Technical Decisions

| 결정 | 선택 | 근거 |
|------|------|------|
| JWT 라이브러리 | python-jose | FastAPI 공식 권장, JOSE 표준 지원 |
| 비밀번호 해싱 | passlib[bcrypt] | 업계 표준, cost factor 12 |
| 세션 저장소 | Redis | Constitution 준수, TTL 자동 만료 |
| Access Token 무효화 | Blacklist (Redis) | 로그아웃 즉시 적용 |
| 계정 잠금 | Redis 카운터 + TTL | DB 부하 없음, 분산 환경 지원 |
| 에러 응답 | RFC 7807 Problem Details | 표준화된 형식 |

## Complexity Tracking

> Constitution 위반 사항 없음. 모든 원칙 준수.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (없음) | - | - |

## Generated Artifacts

| 파일 | 설명 |
|------|------|
| `research.md` | 기술 결정 및 근거 |
| `data-model.md` | User, Session 엔티티 정의 |
| `contracts/openapi.yaml` | REST API 명세 (OpenAPI 3.0) |
| `quickstart.md` | 통합 시나리오 및 사용 예시 |

## Next Steps

1. `/speckit.tasks` 실행하여 구현 태스크 생성
2. `/speckit.analyze` 실행하여 아티팩트 일관성 검증
3. `/speckit.implement` 실행하여 구현 시작
