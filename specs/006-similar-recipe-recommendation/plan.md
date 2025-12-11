# Implementation Plan: 유사 레시피 추천

**Branch**: `006-similar-recipe-recommendation` | **Date**: 2025-12-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-similar-recipe-recommendation/spec.md`

## Summary

유사 레시피 추천 API를 구현한다. 콘텐츠 기반(재료, 태그, 조리법 유사도) 유사 레시피 조회, 같은 요리사의 다른 레시피 조회, 태그 기반 관련 레시피 조회, 같은 카테고리 내 인기 레시피 조회 기능을 제공한다. SQL 기반 유사도 계산을 사용하며, Redis 캐싱으로 성능을 최적화한다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+
**Storage**: PostgreSQL 15+ (단일 DB, 스키마 분리), Redis 7+ (단일 인스턴스)
**Message Queue**: FastAPI BackgroundTasks (필요시 SQS)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux (AWS ECS Fargate)
**Project Type**: Modular Monolith (`app/` 디렉토리 기반)
**Performance Goals**: 유사 레시피 < 300ms (캐시 히트 < 50ms), 같은 요리사 < 100ms
**Constraints**: 동시 1000명 사용자, 캐시 히트율 70% 이상
**Scale/Scope**: recipes 모듈 내 기능 확장

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 | 비고 |
|------|----------|------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ | contracts/ 디렉토리에 정의 예정 |
| II. Modular Monolith | 도메인 경계 명확함? | ✅ | recipes 모듈 내 확장, 추가 테이블 없음 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ | pytest 테스트 작성 예정 |
| IV. Async Task | BackgroundTasks 패턴 준수? | ✅ | 캐시 무효화만 필요, 비동기 작업 없음 |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ | Pydantic 입력 검증, UUID 검증 |
| VI. Observability | 로깅/메트릭/추적 계획됨? | ✅ | 구조화된 로깅 적용, CloudWatch 연동 |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ | SQL 기반 유사도, 벡터 검색은 Phase 2 |

## Project Structure

### Documentation (this feature)

```text
specs/006-similar-recipe-recommendation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── similar-recipes-api.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

내시피 백엔드는 모듈러 모놀리스 구조를 따릅니다:

```text
app/
├── recipes/                 # 레시피 도메인 모듈
│   ├── models.py           # Chef, Recipe, Tag 등 (기존)
│   ├── schemas.py          # 유사 레시피 스키마 추가 (확장)
│   ├── services.py         # 유사 레시피 서비스 추가 (확장)
│   └── router.py           # 유사 레시피 API 라우터 추가 (확장)
├── infra/
│   └── redis.py            # 캐시 클라이언트 (기존)
└── core/
    └── exceptions.py       # 예외 처리 (기존)

tests/
└── recipes/
    ├── test_similar_recipes.py     # 유사 레시피 API 테스트 (신규)
    └── test_same_chef_recipes.py   # 같은 요리사 레시피 테스트 (신규)
```

**기존 서비스 활용**:
- `RecipeService`: 레시피 조회 (기존 get_by_id, get_list 재사용)
- `ChefService`: 요리사 조회 (기존 get_by_id 재사용)
- `RecipeCacheKeys`: 캐시 키 패턴 (확장)

## Complexity Tracking

> 현재 Constitution 위반 사항 없음

## Phase 0 Artifacts

### research.md
- 유사도 계산 알고리즘 비교 (Jaccard, Cosine, SQL 기반)
- 캐싱 전략 및 무효화 정책
- 페이지네이션 및 성능 최적화 패턴

## Phase 1 Artifacts

### data-model.md
- 기존 테이블 사용 (새 테이블 없음)
- 유사도 계산 뷰/CTE 정의 (필요시)

### contracts/similar-recipes-api.yaml
- `GET /api/v1/recipes/{id}/similar` - 유사 레시피
- `GET /api/v1/recipes/{id}/same-chef` - 같은 요리사 레시피
- `GET /api/v1/recipes/{id}/related-by-tags` - 태그 기반 관련 레시피
- `GET /api/v1/recipes/{id}/category-popular` - 카테고리 인기 레시피

### quickstart.md
- 통합 테스트 시나리오
- API 사용 예제
- 캐시 동작 검증

## Next Steps

1. `/speckit.tasks` 실행으로 tasks.md 생성
2. 구현 진행 (router → service → schemas 순서)
3. 테스트 작성 및 검증
4. 캐시 성능 테스트
