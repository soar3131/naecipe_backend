# Implementation Plan: 사용자 프로필 및 취향 설정

**Branch**: `003-user-profile-preferences` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-user-profile-preferences/spec.md`

## Summary

사용자 프로필 조회/수정 및 취향 설정(식이 제한, 알레르기, 맛 취향) 기능을 구현한다. User Service(8002)에 `GET/PUT /users/me` 및 `PUT /users/me/preferences` API를 추가하고, `user_profiles`와 `taste_preferences` 테이블을 생성한다. 기존 User 엔티티와 1:1, 1:N 관계를 맺으며, 사용자 계정 생성 시 기본 프로필이 자동 생성된다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+
**Storage**: PostgreSQL 15+ (User DB), Redis 7+ (세션 캐시)
**Testing**: pytest, pytest-asyncio, httpx (테스트 클라이언트)
**Target Platform**: Linux (AWS EKS)
**Target Service**: user-service (Port 8002)
**Performance Goals**: 프로필 조회 < 100ms, 프로필 수정 < 150ms (p99)
**Constraints**: 500명 동시 요청 처리, 기존 User 모델과 호환

**Existing Dependencies**:
- User 모델 (services/user-service/src/user_service/models/user.py)
- JWT 인증 시스템 (SPEC-001)
- OAuth 계정 연동 (SPEC-002)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ contracts/openapi.yaml 생성 예정 |
| II. Microservice | 도메인 경계 명확함? 독립 배포 가능? | ✅ User Service 내 확장, 독립 배포 유지 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ Schemathesis + pytest 계획 |
| IV. Event-Driven | Kafka 이벤트 스키마 정의됨? | ✅ UserPreferenceUpdated 이벤트 정의 |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ Pydantic 검증, Enum 제한, JWT 인증 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ 기존 로깅/추적 인프라 재사용 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ 직접 ORM 사용, Repository 패턴 미사용 |

## Project Structure

### Documentation (this feature)

```text
specs/003-user-profile-preferences/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # OpenAPI 3.0 스펙
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (user-service)

```text
services/user-service/src/user_service/
├── api/
│   └── v1/
│       ├── users.py         # NEW: GET/PUT /users/me, PUT /users/me/preferences
│       └── router.py        # MODIFY: users 라우터 추가
├── models/
│   ├── user.py              # EXISTING: User 모델
│   ├── user_profile.py      # NEW: UserProfile 모델
│   └── taste_preference.py  # NEW: TastePreference 모델
├── schemas/
│   ├── user.py              # EXISTING
│   ├── profile.py           # NEW: 프로필 요청/응답 스키마
│   └── preference.py        # NEW: 취향 요청/응답 스키마
├── services/
│   ├── profile.py           # NEW: 프로필 비즈니스 로직
│   └── preference.py        # NEW: 취향 비즈니스 로직
└── events/
    └── preference.py        # NEW: UserPreferenceUpdated 이벤트 발행

services/user-service/tests/
├── contract/
│   └── test_users_contract.py  # NEW: API 계약 테스트
└── integration/
    └── test_profile_api.py     # NEW: 통합 테스트
```

## Complexity Tracking

> Constitution Check에서 모든 원칙을 준수하므로 위반 사항 없음.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

## Phase 0: Research (완료)

→ [research.md](./research.md) 참조

## Phase 1: Design (완료)

- [data-model.md](./data-model.md): 엔티티 정의
- [contracts/openapi.yaml](./contracts/openapi.yaml): API 명세
- [quickstart.md](./quickstart.md): 통합 시나리오

## Next Steps

`/speckit.tasks` 명령으로 Phase 2 (구현 태스크) 생성
