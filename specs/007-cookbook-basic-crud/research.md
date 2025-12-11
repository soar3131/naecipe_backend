# Research: 레시피북 기본 CRUD

**Feature Branch**: `007-cookbook-basic-crud`
**Created**: 2025-12-11

## 기술 결정 요약

| 항목 | 결정 | 근거 |
|------|------|------|
| 모듈 위치 | `app/cookbooks/` | 모듈러 모놀리스 구조 준수 |
| 기본 레시피북 생성 방식 | Lazy Creation (첫 접근 시) | 사용자 경험 + 불필요한 데이터 생성 방지 |
| 저장된 레시피 카운트 | 서브쿼리 COUNT | 실시간 정확성 + N+1 방지 |
| sort_order 관리 | 1부터 재할당 | 간격 없는 연속 정렬 보장 |
| Partial Unique Index | PostgreSQL 전용 구현 | is_default=true 단일 보장 |

---

## 연구 1: 기본 레시피북 자동 생성 전략

### 질문

사용자의 기본 레시피북을 언제, 어떻게 생성할 것인가?

### 옵션 분석

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 회원가입 시 생성** | 항상 존재 보장 | 불필요한 레코드 생성, 회원가입 로직 복잡 |
| **B. 첫 접근 시 생성 (Lazy)** | 필요할 때만 생성, 깔끔한 분리 | 첫 요청 약간 느림 |
| **C. 첫 레시피 저장 시** | 실제 사용 시점에만 생성 | 목록 조회 시 생성 안 됨 |

### 결정

**옵션 B: 첫 접근 시 생성 (Lazy Creation)**

### 근거

1. 회원가입 로직과 분리되어 유지보수 용이
2. 실제로 레시피북 기능을 사용하는 사용자에게만 데이터 생성
3. GET /cookbooks, POST /saved-recipes 모두 트리거 가능

### 구현 방식

```python
async def ensure_default_cookbook(user_id: str, session: AsyncSession) -> Cookbook:
    """기본 레시피북이 없으면 생성하고 반환"""
    default = await session.scalar(
        select(Cookbook)
        .where(Cookbook.user_id == user_id, Cookbook.is_default == True)
    )
    if default:
        return default

    # 생성
    new_cookbook = Cookbook(
        user_id=user_id,
        name="내 레시피북",
        is_default=True,
        sort_order=0,
    )
    session.add(new_cookbook)
    await session.flush()
    return new_cookbook
```

---

## 연구 2: 저장된 레시피 수 집계 방식

### 질문

레시피북 목록/상세 조회 시 `saved_recipe_count`를 어떻게 효율적으로 가져올 것인가?

### 옵션 분석

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 필드로 저장 (캐싱)** | 조회 빠름 | 동기화 필요, 정합성 이슈 |
| **B. 서브쿼리 COUNT** | 항상 정확, 구현 간단 | 약간의 추가 쿼리 비용 |
| **C. 별도 요청** | 단순 | N+1 문제, 클라이언트 복잡 |

### 결정

**옵션 B: 서브쿼리 COUNT**

### 근거

1. 레시피북 개수가 많지 않음 (사용자당 최대 50개 권장)
2. 저장된 레시피 수가 자주 변경됨 (피드백, 삭제 등)
3. 실시간 정확성 보장
4. SQLAlchemy로 단일 쿼리 최적화 가능

### 구현 방식

```python
from sqlalchemy import func, select

# 서브쿼리로 카운트
count_subquery = (
    select(func.count(SavedRecipe.id))
    .where(SavedRecipe.cookbook_id == Cookbook.id)
    .correlate(Cookbook)
    .scalar_subquery()
)

query = (
    select(Cookbook, count_subquery.label('saved_recipe_count'))
    .where(Cookbook.user_id == user_id)
    .order_by(Cookbook.sort_order)
)
```

---

## 연구 3: 기본 레시피북 단일성 보장

### 질문

사용자당 정확히 하나의 기본 레시피북(is_default=true)만 존재하도록 어떻게 보장할 것인가?

### 옵션 분석

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 애플리케이션 로직** | DB 독립적 | 동시성 문제 가능 |
| **B. Partial Unique Index** | DB 레벨 강제 | PostgreSQL 전용 |
| **C. 트리거** | 자동 적용 | 복잡, 디버깅 어려움 |

### 결정

**옵션 B: Partial Unique Index**

### 근거

1. PostgreSQL 전용 기능이지만 프로젝트가 PostgreSQL 고정
2. DB 레벨에서 무결성 보장
3. 구현 간단

### 구현 방식

```sql
-- Migration에서 추가
CREATE UNIQUE INDEX uq_cookbooks_user_default
ON cookbooks (user_id)
WHERE is_default = TRUE;
```

```python
# SQLAlchemy 모델에서
__table_args__ = (
    Index(
        'uq_cookbooks_user_default',
        'user_id',
        unique=True,
        postgresql_where=(is_default == True),
    ),
)
```

---

## 연구 4: 순서 변경 알고리즘

### 질문

레시피북 순서 변경(reorder) 시 sort_order를 어떻게 관리할 것인가?

### 옵션 분석

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 간격 기반 (10, 20, 30...)** | 단일 업데이트 | 간격 고갈 시 재정렬 필요 |
| **B. 1부터 재할당** | 항상 정돈됨 | 전체 업데이트 필요 |
| **C. 배열 순서** | 유연 | PostgreSQL 배열 의존 |

### 결정

**옵션 B: 1부터 재할당**

### 근거

1. 레시피북 개수가 적음 (50개 미만)
2. 순서 변경 빈도 낮음
3. 항상 연속적인 순서 보장
4. 로직 단순

### 구현 방식

```python
async def reorder_cookbooks(
    user_id: str,
    cookbook_ids: list[str],
    session: AsyncSession,
) -> list[Cookbook]:
    # 사용자 소유 검증 및 재할당
    for index, cookbook_id in enumerate(cookbook_ids, start=1):
        await session.execute(
            update(Cookbook)
            .where(Cookbook.id == cookbook_id, Cookbook.user_id == user_id)
            .values(sort_order=index)
        )
    await session.flush()

    # 업데이트된 목록 반환
    return await get_cookbooks(user_id, session)
```

---

## 연구 5: 권한 검증 패턴

### 질문

레시피북 접근 시 소유권 검증을 어떻게 구현할 것인가?

### 옵션 분석

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A. 쿼리에 user_id 포함** | 간단, 효율적 | 권한 없음과 존재하지 않음 구분 불가 |
| **B. 별도 권한 체크 후 조회** | 명확한 분리 | 2회 쿼리 |
| **C. 의존성 주입 (get_cookbook)** | 재사용 가능 | 설정 복잡 |

### 결정

**옵션 A: 쿼리에 user_id 포함**

### 근거

1. 단순하고 효율적 (단일 쿼리)
2. 보안상 타인 리소스 존재 여부도 숨김 (404 반환)
3. 대부분의 API에서 일관된 패턴 적용 가능

### 구현 방식

```python
async def get_cookbook_by_id(
    cookbook_id: str,
    user_id: str,
    session: AsyncSession,
) -> Cookbook | None:
    """사용자 소유의 레시피북만 조회 (없거나 권한 없으면 None)"""
    return await session.scalar(
        select(Cookbook)
        .where(Cookbook.id == cookbook_id, Cookbook.user_id == user_id)
    )
```

---

## 기존 코드베이스 참조

### 참고할 패턴

| 모듈 | 파일 | 참고 내용 |
|------|------|----------|
| recipes | `app/recipes/models.py` | 모델 구조, TimestampMixin |
| recipes | `app/recipes/services.py` | 서비스 레이어 패턴 |
| recipes | `app/recipes/router.py` | 라우터 구조, 의존성 주입 |
| users | `app/users/models.py` | User 모델 관계 |

### 재사용 컴포넌트

- `app/infra/database.py`: Base, TimestampMixin
- `app/core/dependencies.py`: get_current_user
- `app/core/security.py`: JWT 검증

---

## 미해결 사항

없음. 모든 기술 결정 완료.

---

## 다음 단계

1. ✅ research.md 완료
2. → data-model.md 검토 (이미 작성됨, 연구 결과 반영 확인)
3. → contracts/ 검토 (이미 작성됨)
4. → plan.md 완성
