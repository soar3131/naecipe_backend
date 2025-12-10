# Implementation Plan: 원본 레시피 기본 CRUD

**Branch**: `004-recipe-basic-crud` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-recipe-basic-crud/spec.md`

## Summary

Recipe Service(8001)에서 크롤링으로 수집된 원본 레시피와 요리사 정보를 조회하는 API를 구현한다. 레시피 상세/목록/인기 조회, 요리사 목록/상세/인기 조회, 요리사별 레시피 조회를 지원하며, Redis 캐싱을 통해 성능을 최적화한다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+, redis[hiredis]
**Storage**: PostgreSQL 15+ (Recipe DB), Redis 7+ (캐싱)
**Message Queue**: N/A (조회 전용 서비스)
**Testing**: pytest, pytest-asyncio, httpx (TestClient)
**Target Platform**: Linux (AWS EKS)
**Project Type**: microservices (services/recipe-service)
**Performance Goals**: 상세 < 100ms (p99), 목록 < 200ms (p99)
**Constraints**: 동시 1,000명 조회 처리
**Scale/Scope**: Recipe Service 단일 서비스, Phase 1 MVP

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ contracts/openapi.yaml |
| II. Microservice | 도메인 경계 명확함? 독립 배포 가능? | ✅ Recipe Service 독립 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ pytest 테스트 계획 |
| IV. Event-Driven | Kafka 이벤트 스키마 정의됨? | ⬜ N/A (조회 전용) |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ Pydantic 검증 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ 구조화 로깅 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ 직접 구현 |

## Project Structure

### Documentation (this feature)

```text
specs/004-recipe-basic-crud/
├── spec.md              # 기능 명세
├── plan.md              # This file
├── research.md          # 기술 결정
├── data-model.md        # 엔티티 모델
├── quickstart.md        # 통합 시나리오
├── contracts/           # OpenAPI 스펙
│   └── openapi.yaml
├── checklists/          # 체크리스트
│   └── requirements.md
└── tasks.md             # (speckit.tasks에서 생성)
```

### Source Code (repository root)

```text
services/recipe-service/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── recipes.py       # 레시피 API 라우터
│   │   └── chefs.py         # 요리사 API 라우터
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chef.py          # Chef, ChefPlatform 모델
│   │   ├── recipe.py        # Recipe 모델
│   │   ├── ingredient.py    # RecipeIngredient 모델
│   │   ├── step.py          # CookingStep 모델
│   │   └── tag.py           # Tag, RecipeTag 모델
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chef.py          # Chef Pydantic 스키마
│   │   ├── recipe.py        # Recipe Pydantic 스키마
│   │   └── pagination.py    # 커서 페이지네이션 스키마
│   ├── services/
│   │   ├── __init__.py
│   │   ├── recipe_service.py    # 레시피 비즈니스 로직
│   │   └── chef_service.py      # 요리사 비즈니스 로직
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_cache.py   # Redis 캐시 유틸리티
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── contract/            # API 계약 테스트
│   ├── integration/         # 통합 테스트
│   └── unit/                # 단위 테스트
├── Dockerfile
└── pyproject.toml
```

## Phase 0: Research Summary

See [research.md](./research.md) for detailed decisions.

### Key Decisions

1. **커서 기반 페이지네이션**: Offset 대신 Cursor 방식 채택 (성능, 무한 스크롤 지원)
2. **Redis 캐싱 전략**: Cache-Aside 패턴, TTL 1시간
3. **N+1 쿼리 방지**: SQLAlchemy selectinload/joinedload 사용
4. **응답 스키마 분리**: List용 간략 스키마 vs Detail용 상세 스키마

## Phase 1: Design Artifacts

### Data Model

See [data-model.md](./data-model.md) for entity details.

**Core Entities**:
- Chef (요리사)
- ChefPlatform (요리사 플랫폼)
- Recipe (원본 레시피)
- RecipeIngredient (재료)
- CookingStep (조리 단계)
- Tag (태그)
- RecipeTag (레시피-태그 연결)

### API Contracts

See [contracts/openapi.yaml](./contracts/openapi.yaml) for full specification.

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| GET | /recipes | 레시피 목록 (커서 페이지네이션) |
| GET | /recipes/{id} | 레시피 상세 |
| GET | /recipes/popular | 인기 레시피 |
| GET | /chefs | 요리사 목록 |
| GET | /chefs/{id} | 요리사 상세 |
| GET | /chefs/{id}/recipes | 요리사별 레시피 |
| GET | /chefs/popular | 인기 요리사 |

### Integration Scenario

See [quickstart.md](./quickstart.md) for step-by-step guide.

## Complexity Tracking

> No Constitution violations. All principles satisfied.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

## Next Steps

1. Run `/speckit.tasks` to generate task breakdown
2. Implement tasks in order (Setup → Foundational → User Stories → Polish)
3. Run tests and verify Constitution compliance
