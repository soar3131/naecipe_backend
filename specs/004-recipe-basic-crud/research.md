# Research: 원본 레시피 기본 CRUD

**Branch**: `004-recipe-basic-crud` | **Date**: 2025-12-10

## Overview

SPEC-004 구현을 위한 기술 결정 및 연구 결과를 문서화한다.

---

## Decision 1: 페이지네이션 방식

### Decision
**커서 기반 페이지네이션(Cursor-based Pagination)** 채택

### Rationale
- **성능**: OFFSET 방식은 데이터 증가 시 O(n) 스캔 발생, 커서 방식은 인덱스 기반 O(log n)
- **일관성**: 실시간 데이터 추가 시 OFFSET은 중복/누락 발생, 커서는 일관된 결과 보장
- **무한 스크롤**: 프론트엔드 무한 스크롤 UX에 최적화
- **Constitution VI**: 응답 시간 SLA (목록 < 200ms) 충족에 유리

### Alternatives Considered
| 방식 | 장점 | 단점 |
|------|------|------|
| OFFSET | 구현 간단, 페이지 번호 지원 | 성능 저하, 데이터 불일치 |
| Keyset | 안정적 성능 | 정렬 키 필수, 복잡한 정렬 제한 |
| **Cursor (선택)** | 안정적 성능, 유연한 정렬 | Base64 인코딩 오버헤드 |

### Implementation Notes
```python
# 커서 인코딩: (exposure_score, created_at, id) → Base64
cursor = base64.b64encode(f"{score}:{created_at}:{id}".encode()).decode()

# 쿼리 조건: WHERE (exposure_score, created_at, id) < (decoded_cursor)
```

---

## Decision 2: 캐싱 전략

### Decision
**Cache-Aside 패턴** + **Redis** 사용

### Rationale
- **성능**: 레시피 상세 100ms 목표 달성 (DB 조회 평균 50ms + 캐시 조회 5ms)
- **Constitution VII**: 단순 패턴으로 복잡성 최소화
- **일관성**: TTL 기반 자동 갱신으로 데이터 신선도 유지

### Cache Configuration
| 캐시 키 | TTL | 설명 |
|---------|-----|------|
| `recipe:{id}` | 1h | 레시피 상세 |
| `recipes:list:{hash}` | 5m | 레시피 목록 (쿼리 해시) |
| `recipes:popular:{category}` | 10m | 인기 레시피 |
| `chef:{id}` | 1h | 요리사 상세 |
| `chefs:popular` | 10m | 인기 요리사 |

### Invalidation Strategy
- **Manual**: 레시피/요리사 업데이트 시 해당 캐시 삭제 (Ingestion Service에서 처리)
- **TTL**: 자동 만료로 신선도 유지
- **Pattern**: `SCAN` + `DEL`로 패턴 기반 삭제

### Alternatives Considered
| 패턴 | 장점 | 단점 |
|------|------|------|
| Cache-Aside | 단순, 명시적 제어 | 캐시 미스 시 DB 부하 |
| Write-Through | 일관성 보장 | 쓰기 지연, 불필요한 캐싱 |
| **Cache-Aside (선택)** | 조회 전용 서비스에 적합 | - |

---

## Decision 3: N+1 쿼리 방지

### Decision
**SQLAlchemy selectinload/joinedload** 사용

### Rationale
- **성능**: 레시피 상세 조회 시 1개 레시피 + N개 재료 + M개 단계 = 1+1+1 쿼리로 최적화
- **Constitution VI**: 응답 시간 SLA 충족
- **유지보수**: ORM 레벨에서 명시적 로딩 전략

### Implementation
```python
# 레시피 상세 조회
query = (
    select(Recipe)
    .options(
        selectinload(Recipe.ingredients),
        selectinload(Recipe.steps),
        selectinload(Recipe.tags).selectinload(RecipeTag.tag),
        joinedload(Recipe.chef).selectinload(Chef.platforms),
    )
    .where(Recipe.id == recipe_id)
)
```

### Query Comparison
| 시나리오 | Lazy Loading | Eager Loading |
|---------|--------------|---------------|
| 레시피 상세 (재료 5개, 단계 8개, 태그 3개) | 17 쿼리 | 4 쿼리 |
| 레시피 목록 (20개, 각 요리사 포함) | 41 쿼리 | 2 쿼리 |

---

## Decision 4: 응답 스키마 분리

### Decision
**List용 간략 스키마** vs **Detail용 상세 스키마** 분리

### Rationale
- **성능**: 목록 조회 시 불필요한 데이터(재료, 조리 단계) 전송 방지
- **대역폭**: 평균 응답 크기 80% 감소 (상세 5KB → 목록 1KB)
- **Constitution VII**: 필요한 데이터만 반환

### Schema Structure
```python
# 목록용 (간략)
class RecipeListItem(BaseModel):
    id: UUID
    title: str
    thumbnail_url: str | None
    cooking_time_minutes: int
    difficulty: str
    avg_rating: float
    chef_name: str  # 요리사 이름만

# 상세용 (전체)
class RecipeDetail(BaseModel):
    id: UUID
    title: str
    description: str
    # ... 모든 필드
    ingredients: list[IngredientSchema]
    steps: list[StepSchema]
    tags: list[TagSchema]
    chef: ChefSummary
```

---

## Decision 5: 인기도 정렬

### Decision
**exposure_score 컬럼** 기반 정렬

### Rationale
- **성능**: 단일 컬럼 인덱스로 빠른 정렬
- **확장성**: 배치 프로세스에서 복합 점수 계산 (조회수, 저장수, 조리수)
- **Constitution VII**: 조회 시점에 복잡한 계산 회피

### Score Formula (Ingestion Service에서 계산)
```
exposure_score = (view_count × 0.3) + (save_count × 0.4) + (cook_count × 0.3)
```

### Index
```sql
CREATE INDEX idx_recipes_exposure_score ON recipes(exposure_score DESC) WHERE is_active = true;
CREATE INDEX idx_recipes_chef_id ON recipes(chef_id);
CREATE INDEX idx_chefs_recipe_count ON chefs(recipe_count DESC);
```

---

## Decision 6: 오류 처리

### Decision
**HTTP 표준 상태 코드** + **일관된 오류 응답 형식**

### Rationale
- **일관성**: 전체 서비스 통일된 오류 형식
- **디버깅**: 상세 오류 코드로 문제 추적 용이
- **Constitution V**: 보안상 민감 정보 노출 방지

### Error Response Format
```json
{
  "error": {
    "code": "RECIPE_NOT_FOUND",
    "message": "레시피를 찾을 수 없습니다",
    "details": {
      "recipe_id": "uuid-here"
    }
  }
}
```

### Status Codes
| 상태 코드 | 사용 케이스 |
|-----------|------------|
| 200 | 성공 |
| 400 | 잘못된 요청 (커서 형식 오류 등) |
| 404 | 리소스 없음 (레시피/요리사) |
| 500 | 서버 오류 |

---

## Decision 7: 요리사-레시피 조인 전략

### Decision
**Left Join** + **Optional 관계**

### Rationale
- **데이터 무결성**: 요리사 없는 레시피도 조회 가능 (chef_id가 NULL인 경우)
- **유연성**: 요리사 데이터 수집 전 레시피 먼저 저장 가능
- **Constitution II**: 서비스 간 느슨한 결합

### Implementation
```python
# Recipe 모델
class Recipe(Base):
    chef_id: Mapped[UUID | None] = mapped_column(ForeignKey("chefs.id"), nullable=True)
    chef: Mapped["Chef | None"] = relationship(back_populates="recipes")
```

---

## Summary

| 결정 | 선택 | 핵심 이유 |
|------|------|----------|
| 페이지네이션 | 커서 기반 | 성능, 무한 스크롤 |
| 캐싱 | Cache-Aside + Redis | 단순성, 조회 전용 |
| N+1 방지 | selectinload | 쿼리 최적화 |
| 스키마 | 목록/상세 분리 | 대역폭 최적화 |
| 인기도 | exposure_score | 사전 계산, 빠른 정렬 |
| 오류 처리 | HTTP 표준 + 구조화 | 일관성, 보안 |
| 조인 | Left Join | 유연성 |
