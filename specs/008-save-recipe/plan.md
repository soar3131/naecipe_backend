# Implementation Plan: 레시피 저장 (원본 레시피 → 레시피북)

**Branch**: `008-save-recipe` | **Date**: 2025-12-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-save-recipe/spec.md`

## Summary

원본 레시피를 사용자의 레시피북에 저장하고 관리하는 기능을 구현합니다. SavedRecipe 엔티티를 통해 Cookbook과 Recipe 간의 참조 관계를 생성하며, 개인 메모 추가/수정, 목록/상세 조회, 삭제 기능을 제공합니다.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+
**Storage**: PostgreSQL 15+ (단일 인스턴스)
**Cache**: Redis 7+ (단일 인스턴스)
**Async Processing**: FastAPI BackgroundTasks
**Testing**: pytest, pytest-asyncio
**Target Platform**: Linux (AWS ECS Fargate)
**Project Type**: Modular Monolith (app/ 디렉토리 기반)
**Performance Goals**: 저장 < 500ms, 목록 조회 < 200ms (p99)
**Scale/Scope**: cookbooks 모듈에 SavedRecipe 추가

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution 원칙 준수 여부를 확인합니다 (`.specify/memory/constitution.md` 참조):

| 원칙 | 검증 항목 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 스펙 정의됨? | ✅ contracts/openapi.yaml |
| II. Modular Monolith | 도메인 경계 명확함? 스키마 분리? | ✅ cookbooks 모듈에 SavedRecipe 추가 |
| III. TDD | Contract/Integration 테스트 계획됨? | ✅ tests/cookbooks/test_saved_recipe*.py |
| IV. Async Task | BackgroundTasks 사용 계획됨? | ✅ 현재 동기 처리, 향후 필요시 BackgroundTasks |
| V. Security | OWASP 대응, 입력 검증 계획됨? | ✅ Pydantic 검증, 소유권 확인 |
| VI. Observability | 로깅/메트릭 계획됨? | ✅ 구조화 로깅 (CloudWatch) |
| VII. Simplicity | 불필요한 추상화 없음? | ✅ 기존 패턴 재사용 |

## Project Structure

### Documentation (this feature)

```text
specs/008-save-recipe/
├── spec.md              # Feature specification ✅
├── plan.md              # This file ✅
├── research.md          # Technical decisions ✅
├── data-model.md        # Entity design ✅
├── quickstart.md        # Integration scenarios ✅
├── contracts/           # API specification ✅
│   └── openapi.yaml
├── checklists/          # Quality checklists ✅
│   └── requirements.md
└── tasks.md             # Execution tasks (by /speckit.tasks)
```

### Source Code (repository root)

내시피 백엔드는 모듈러 모놀리스 구조를 따릅니다:

```text
app/
├── core/                    # 공유 설정, 보안, 의존성
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
├── infra/                   # 인프라 레이어 (DB, Redis, S3)
│   ├── database.py
│   ├── redis.py
│   └── s3.py
├── cookbooks/               # 레시피북 도메인 모듈 ← SavedRecipe 추가
│   ├── models.py            # Cookbook + SavedRecipe 모델
│   ├── schemas.py           # Cookbook + SavedRecipe 스키마
│   ├── services.py          # Cookbook + SavedRecipe 서비스
│   ├── router.py            # Cookbook + SavedRecipe 라우터
│   └── exceptions.py        # 커스텀 예외
├── recipes/                 # 레시피 도메인 모듈 (원본 레시피)
│   ├── models.py            # Recipe, Chef, Ingredient, Step, Tag
│   ├── schemas.py
│   ├── services.py
│   └── router.py
├── users/                   # 사용자 도메인 모듈
└── main.py                  # FastAPI 앱 진입점

tests/
└── cookbooks/
    ├── conftest.py              # 테스트 픽스처 (SavedRecipe 추가)
    ├── test_cookbook_crud.py    # 기존 Cookbook 테스트
    ├── test_cookbook_service.py # 기존 Cookbook 서비스 테스트
    ├── test_saved_recipe_crud.py    # SavedRecipe 통합 테스트 (NEW)
    └── test_saved_recipe_service.py # SavedRecipe 서비스 테스트 (NEW)
```

## Implementation Approach

### Phase 1: Setup (프로젝트 설정)

1. Alembic 마이그레이션 생성 (`saved_recipes` 테이블)
2. SavedRecipe 모델 추가 (`app/cookbooks/models.py`)
3. SavedRecipe 스키마 추가 (`app/cookbooks/schemas.py`)
4. SavedRecipe 예외 추가 (`app/cookbooks/exceptions.py`)
5. 테스트 픽스처 확장 (`tests/cookbooks/conftest.py`)

### Phase 2: Foundational (기반 인프라)

1. SavedRecipeService 클래스 스켈레톤
2. RecipeService 연동 (레시피 존재 확인)
3. CookbookService 확장 (소유권 검증 재사용)

### Phase 3-6: User Stories (P1 → P2 → P3)

각 User Story별로:
1. 테스트 작성 (실패)
2. 서비스 구현
3. 라우터 엔드포인트 추가
4. 테스트 통과 확인

### Phase 7: Polish

1. 구조화 로깅 추가
2. OpenAPI 문서 주석
3. 전체 테스트 실행 및 검증

## Complexity Tracking

> **Constitution 위반 없음** - 모든 원칙 준수

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| 모듈 위치 | cookbooks 모듈 | SavedRecipe는 Cookbook과 밀접, 도메인 경계 유지 |
| 중복 방지 | DB UNIQUE 제약 | 동시성 안전, 단순 구현 |
| 삭제 정책 | CASCADE | Cookbook 삭제 시 SavedRecipe도 삭제 |

## Dependencies

### 선행 스펙

- **SPEC-007**: 레시피북 기본 CRUD ✅ 완료
- **SPEC-004**: 원본 레시피 기본 CRUD ✅ 완료

### 기술 의존성

- Cookbook 모델/서비스 (SPEC-007)
- Recipe 모델 (SPEC-004)
- 인증 시스템 (core/security.py)

## Generated Artifacts

- `specs/008-save-recipe/research.md` - 기술 결정 사항
- `specs/008-save-recipe/data-model.md` - 엔티티 설계
- `specs/008-save-recipe/contracts/openapi.yaml` - API 명세
- `specs/008-save-recipe/quickstart.md` - 통합 시나리오

## Next Steps

```bash
/speckit.tasks    # 실행 가능한 태스크 생성
/speckit.implement  # 구현 시작
```
