# Implementation Plan: OAuth 소셜 로그인

**Branch**: `002-oauth-social-login` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-oauth-social-login/spec.md`

## Summary

카카오, 구글, 네이버 OAuth2.0 소셜 로그인 기능을 구현하여 사용자가 기존 소셜 계정으로 간편하게 서비스에 로그인할 수 있도록 한다. SPEC-001에서 구현된 JWT 토큰 발급 및 Redis 세션 관리 로직을 재사용하며, 새로운 `oauth_accounts` 테이블을 추가하여 소셜 계정 정보를 관리한다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy, Pydantic, httpx (OAuth HTTP 클라이언트)
**Storage**: PostgreSQL 15+ (user-service DB), Redis 7+ (세션/state 관리)
**Message Queue**: 이 스펙에서는 Kafka 이벤트 발행 없음 (인증 이벤트는 SPEC-003 이후)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux (AWS EKS)
**Project Type**: microservices (services/user-service)
**Performance Goals**: OAuth 콜백 처리 < 1초 (제공자 응답 시간 제외)
**Constraints**: 가용성 99.9%, CSRF 공격 방지 필수
**Scale/Scope**: user-service 확장, 단일 서비스 범위

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ contracts/openapi.yaml 생성 예정 |
| II. Microservice | 도메인 경계 명확함? 독립 배포 가능? | ✅ user-service 내 확장, 독립 배포 가능 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ OAuth 콜백 테스트, Mock Provider 테스트 |
| IV. Event-Driven | Kafka 이벤트 스키마 정의됨? | ⬜ 해당 없음 (이 스펙에서 이벤트 발행 없음) |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ state 파라미터 CSRF 방지, Pydantic 검증 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ 구조화 로깅, OAuth 에러 추적 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ 제공자별 직접 구현, 복잡한 추상화 없음 |

## Project Structure

### Documentation (this feature)

```text
specs/002-oauth-social-login/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # OAuth API 명세
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
services/user-service/
├── src/user_service/
│   ├── api/
│   │   └── oauth.py            # OAuth 라우터 (신규)
│   ├── models/
│   │   └── oauth_account.py    # OAuthAccount 모델 (신규)
│   ├── schemas/
│   │   └── oauth.py            # OAuth 스키마 (신규)
│   ├── services/
│   │   └── oauth.py            # OAuth 서비스 (신규)
│   └── core/
│       └── oauth_providers.py  # 제공자별 설정 (신규)
├── alembic/versions/
│   └── 002_create_oauth_accounts.py  # 마이그레이션 (신규)
└── tests/
    ├── integration/
    │   └── test_oauth.py       # OAuth 통합 테스트
    └── unit/
        └── test_oauth_service.py
```

## Complexity Tracking

> 위반 사항 없음. 단순한 OAuth 구현으로 불필요한 추상화 없이 진행.
