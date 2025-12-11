# Research: 레시피 저장 기능

**Feature Branch**: `008-save-recipe`
**Date**: 2025-12-11

## 기술 결정 사항

### 1. SavedRecipe 모델 위치

**Decision**: `app/cookbooks/models.py`에 SavedRecipe 모델 추가

**Rationale**:
- SavedRecipe는 Cookbook과 밀접한 관계 (Cookbook.saved_recipes)
- cookbooks 모듈이 "사용자의 레시피 컬렉션" 도메인 담당
- Recipe 모듈은 "원본 레시피 데이터" 도메인 유지

**Alternatives Considered**:
- `app/recipes/models.py`에 추가 → 거부: 도메인 경계 위반 (사용자 데이터 vs 원본 데이터)
- 별도 `app/saved_recipes/` 모듈 → 거부: 과도한 분리, Cookbook과의 강한 결합

### 2. 중복 저장 방지 전략

**Decision**: DB 레벨 UNIQUE 제약 (cookbook_id, original_recipe_id)

**Rationale**:
- 동시 요청에도 데이터 무결성 보장
- 애플리케이션 레벨 검사보다 안정적
- IntegrityError 캐치로 409 Conflict 반환

**Alternatives Considered**:
- 애플리케이션 레벨 중복 체크 → 거부: Race condition 가능성
- Upsert (ON CONFLICT) → 거부: 명세에서 409 반환 요구

### 3. 원본 레시피 정보 조회 전략

**Decision**: SavedRecipe 조회 시 Recipe JOIN (lazy="joined" 또는 selectinload)

**Rationale**:
- 목록 조회 시 N+1 쿼리 방지
- 원본 레시피 title, thumbnail 등 필수 정보 포함
- 상세 조회 시 전체 Recipe 정보 포함

**Alternatives Considered**:
- SavedRecipe에 title, thumbnail 복사 저장 → 거부: 데이터 중복, 동기화 문제
- GraphQL DataLoader 패턴 → 거부: REST API 사용, 과도한 복잡성

### 4. CASCADE 삭제 정책

**Decision**:
- Cookbook 삭제 → SavedRecipe CASCADE 삭제
- SavedRecipe 삭제 → RecipeVariation CASCADE 삭제 (SPEC-009 대비)
- Recipe 삭제 → SavedRecipe에서 original_recipe_id SET NULL 또는 유지

**Rationale**:
- 레시피북 삭제 시 저장된 레시피도 삭제는 자연스러움
- 원본 레시피 삭제 시 저장된 레시피 유지 (사용자 데이터 보호)

**Alternatives Considered**:
- Recipe 삭제 시 SavedRecipe도 CASCADE → 거부: 사용자 데이터 손실
- 소프트 삭제 → 거부: Constitution VII (Simplicity) 위반

### 5. 페이지네이션 전략

**Decision**: Offset-based 페이지네이션 (limit, offset 파라미터)

**Rationale**:
- 기존 SPEC-007 Cookbook 목록과 일관성
- 단순한 구현, 대부분의 사용 사례에 충분
- 사용자당 저장 레시피 수가 1000개 미만 예상

**Alternatives Considered**:
- Cursor-based 페이지네이션 → 거부: 현재 규모에서 과잉 복잡성
- Infinite scroll → 거부: API는 페이지네이션 제공, UI 결정은 프론트엔드

### 6. 정렬 기준

**Decision**: 기본 정렬 = created_at DESC (최신 저장순)

**Rationale**:
- 사용자 직관에 부합 (최근 저장한 것이 위에)
- 추가 정렬 옵션은 향후 확장 가능

**Alternatives Considered**:
- 사용자 정의 sort_order → 거부: SPEC-008 범위 외, 추후 고려
- 원본 레시피 인기순 → 거부: 개인 컬렉션에서는 저장 시간이 더 중요

### 7. 메모 유효성 검사

**Decision**: 최대 1000자, nullable, 빈 문자열 허용

**Rationale**:
- 1000자는 상세한 메모에 충분
- nullable과 빈 문자열 구분으로 유연성 확보
- Pydantic Field(max_length=1000) 사용

**Alternatives Considered**:
- HTML 지원 → 거부: XSS 위험, Constitution V (Security) 고려
- 마크다운 지원 → 거부: 프론트엔드 렌더링 복잡성, 향후 확장 가능

## 의존성 분석

### 기존 모듈 활용

| 모듈 | 활용 내용 |
|------|----------|
| `app/cookbooks/` | Cookbook 모델, CookbookService (권한 검증) |
| `app/recipes/` | Recipe 모델 (원본 레시피 참조) |
| `app/core/security.py` | get_current_user 의존성 |
| `app/infra/database.py` | Base, TimestampMixin, AsyncSession |

### 새로 생성할 컴포넌트

| 컴포넌트 | 파일 | 설명 |
|---------|------|------|
| SavedRecipe 모델 | `app/cookbooks/models.py` | 저장된 레시피 엔티티 |
| SavedRecipe 스키마 | `app/cookbooks/schemas.py` | 요청/응답 스키마 |
| SavedRecipeService | `app/cookbooks/services.py` | 비즈니스 로직 |
| SavedRecipe 라우터 | `app/cookbooks/router.py` | API 엔드포인트 |
| SavedRecipe 예외 | `app/cookbooks/exceptions.py` | 커스텀 예외 |

## 미해결 사항

없음 - 모든 기술 결정 완료
