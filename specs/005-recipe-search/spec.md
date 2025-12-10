# Feature Specification: 원본 레시피 검색

**Feature Branch**: `005-recipe-search`
**Created**: 2025-12-10
**Status**: Implemented
**Input**: SPEC-005 - 원본 레시피 검색: 키워드 검색, 필터링, 정렬, 커서 기반 페이지네이션

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 키워드로 레시피 검색 (Priority: P1)

사용자가 검색창에 키워드를 입력하여 원하는 레시피를 찾는 시나리오입니다.
검색어는 레시피 제목, 설명, 재료명, 요리사명에서 매칭됩니다.

**Why this priority**: 검색은 Core Loop의 시작점이며, 사용자가 원하는 레시피를 찾는 가장 기본적인 방법입니다. 이 기능 없이는 서비스 이용이 불가능합니다.

**Independent Test**: 검색 API를 호출하여 키워드와 일치하는 레시피 목록이 반환되는지 검증. 단독으로 테스트 가능하며 검색 결과 페이지 기능을 제공합니다.

**Acceptance Scenarios**:

1. **Given** 활성화된 레시피 "김치찌개"가 존재할 때, **When** 사용자가 "김치"로 검색하면, **Then** "김치찌개" 레시피가 검색 결과에 포함됩니다.
2. **Given** 재료에 "돼지고기"가 포함된 레시피가 존재할 때, **When** 사용자가 "돼지고기"로 검색하면, **Then** 해당 레시피가 검색 결과에 포함됩니다.
3. **Given** 요리사 "백종원"의 레시피가 존재할 때, **When** 사용자가 "백종원"으로 검색하면, **Then** 백종원의 레시피들이 검색 결과에 포함됩니다.
4. **Given** 검색어와 일치하는 레시피가 없을 때, **When** 사용자가 검색하면, **Then** 빈 목록과 함께 has_more=false가 반환됩니다.

---

### User Story 2 - 필터링으로 검색 결과 좁히기 (Priority: P1)

사용자가 다양한 조건(난이도, 조리시간, 태그, 요리사)으로 검색 결과를 필터링하는 시나리오입니다.

**Why this priority**: 검색 결과가 많을 때 원하는 레시피를 빠르게 찾기 위해 필수적인 기능입니다. 키워드 검색과 함께 사용될 때 가장 효과적입니다.

**Independent Test**: 각 필터 조건별로 API를 호출하여 조건에 맞는 레시피만 반환되는지 검증.

**Acceptance Scenarios**:

1. **Given** 난이도가 "easy", "medium", "hard"인 레시피들이 존재할 때, **When** `difficulty=easy`로 필터링하면, **Then** 난이도가 "easy"인 레시피만 반환됩니다.
2. **Given** 조리시간이 다양한 레시피들이 존재할 때, **When** `max_cook_time=30`으로 필터링하면, **Then** 조리시간이 30분 이하인 레시피만 반환됩니다.
3. **Given** "한식" 태그가 있는 레시피들이 존재할 때, **When** `tag=한식`으로 필터링하면, **Then** "한식" 태그가 있는 레시피만 반환됩니다.
4. **Given** 요리사 "백종원"의 레시피들이 존재할 때, **When** `chef_id={백종원_id}`로 필터링하면, **Then** 백종원의 레시피만 반환됩니다.
5. **Given** 여러 필터 조건이 적용될 때, **When** `difficulty=easy&tag=한식`으로 필터링하면, **Then** 두 조건을 모두 만족하는 레시피만 반환됩니다 (AND 조건).

---

### User Story 3 - 검색 결과 정렬 (Priority: P2)

사용자가 검색 결과를 다양한 기준으로 정렬하는 시나리오입니다.

**Why this priority**: 기본 정렬(종합 스코어)로 충분히 사용 가능하지만, 사용자 선호에 따른 정렬 옵션은 UX 향상에 기여합니다.

**Independent Test**: 각 정렬 기준별로 API를 호출하여 정렬 순서가 올바른지 검증.

**Acceptance Scenarios**:

1. **Given** 검색 결과가 존재할 때, **When** `sort=relevance`(기본값)으로 정렬하면, **Then** 검색어 관련도 + 노출 점수 기준으로 정렬됩니다.
2. **Given** 검색 결과가 존재할 때, **When** `sort=latest`로 정렬하면, **Then** 생성일 내림차순으로 정렬됩니다.
3. **Given** 검색 결과가 존재할 때, **When** `sort=cook_time`로 정렬하면, **Then** 조리시간 오름차순으로 정렬됩니다.
4. **Given** 검색 결과가 존재할 때, **When** `sort=popularity`로 정렬하면, **Then** 조회수/저장수 기반 인기순으로 정렬됩니다.

---

### User Story 4 - 무한 스크롤 페이지네이션 (Priority: P2)

사용자가 검색 결과를 스크롤하며 추가 결과를 로드하는 시나리오입니다.

**Why this priority**: 첫 페이지 결과만으로도 검색 기능은 동작하지만, 많은 결과를 탐색하려면 페이지네이션이 필요합니다.

**Independent Test**: 커서 기반 페이지네이션 API를 호출하여 다음 페이지가 올바르게 로드되는지 검증.

**Acceptance Scenarios**:

1. **Given** 검색 결과가 25개이고 limit=20일 때, **When** 첫 번째 요청을 하면, **Then** 20개 결과와 `next_cursor`, `has_more=true`가 반환됩니다.
2. **Given** 첫 번째 응답에서 `next_cursor`를 받았을 때, **When** 해당 커서로 다음 요청을 하면, **Then** 나머지 5개 결과와 `has_more=false`가 반환됩니다.
3. **Given** 검색 결과가 10개이고 limit=20일 때, **When** 요청하면, **Then** 10개 결과와 `has_more=false`, `next_cursor=null`이 반환됩니다.

---

### User Story 5 - 검색 결과 캐싱 (Priority: P3)

동일한 검색 조건에 대해 캐시된 결과를 빠르게 반환하는 시나리오입니다.

**Why this priority**: 성능 최적화 기능으로, 기본 검색 기능이 완성된 후 추가됩니다.

**Independent Test**: 동일한 검색 요청을 두 번 수행하여 두 번째 요청의 응답 시간이 더 빠른지 검증.

**Acceptance Scenarios**:

1. **Given** 동일한 검색 조건으로 이전에 검색한 적이 있을 때, **When** 같은 검색을 다시 수행하면, **Then** 캐시된 결과가 반환됩니다 (5분 TTL).
2. **Given** 캐시된 검색 결과가 있을 때, **When** 새 레시피가 추가되면, **Then** 관련 캐시가 무효화됩니다.

---

### Edge Cases

- **빈 검색어**: 검색어 없이 필터만 적용하면 전체 레시피 목록에서 필터링 (키워드 검색 생략)
- **특수 문자 검색어**: SQL Injection 방지 및 특수 문자 이스케이프 처리
- **매우 긴 검색어**: 검색어 길이 제한 (최대 100자)
- **동시 필터 충돌**: 조건을 만족하는 결과가 없으면 빈 목록 반환
- **존재하지 않는 chef_id 필터**: 빈 목록 반환 (에러 아님)
- **유효하지 않은 정렬 옵션**: 400 Bad Request 반환
- **음수 조리시간 필터**: 400 Bad Request 반환

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST 키워드로 레시피를 검색할 수 있어야 합니다 (제목, 설명, 재료명, 요리사명)
- **FR-002**: System MUST 난이도 필터링을 지원해야 합니다 (easy, medium, hard)
- **FR-003**: System MUST 최대 조리시간 필터링을 지원해야 합니다 (분 단위)
- **FR-004**: System MUST 태그 필터링을 지원해야 합니다
- **FR-005**: System MUST 요리사 필터링을 지원해야 합니다 (chef_id)
- **FR-006**: System MUST 여러 필터의 AND 조합을 지원해야 합니다
- **FR-007**: System MUST 커서 기반 페이지네이션을 지원해야 합니다
- **FR-008**: System MUST 검색 결과에 요리사 정보 (id, name, profile_image_url)를 포함해야 합니다
- **FR-009**: System MUST 비활성화된 레시피 (is_active=false)를 검색 결과에서 제외해야 합니다
- **FR-010**: System MUST 정렬 옵션을 지원해야 합니다 (relevance, latest, cook_time, popularity)
- **FR-011**: System SHOULD 검색 결과를 캐싱해야 합니다 (Redis, TTL 5분)
- **FR-012**: System MUST 검색어 길이를 100자 이하로 제한해야 합니다
- **FR-013**: System MUST SQL Injection 및 특수 문자를 안전하게 처리해야 합니다

### Non-Functional Requirements

- **NFR-001**: 검색 응답 시간은 p99 기준 200ms 이하여야 합니다
- **NFR-002**: 검색 API는 초당 1000 요청을 처리할 수 있어야 합니다
- **NFR-003**: 검색 결과 캐시 TTL은 5분입니다

### Key Entities

- **SearchQuery**: 검색 요청 파라미터 (keyword, filters, sort, pagination)
- **SearchResult**: 검색 응답 (items, next_cursor, has_more, total_count)
- **SearchFilter**: 필터 조건 (difficulty, max_cook_time, tag, chef_id)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자가 검색어로 원하는 레시피를 3초 내에 찾을 수 있습니다
- **SC-002**: 검색 API 응답 시간이 p99 기준 200ms 이하입니다
- **SC-003**: 모든 필터 조합이 올바르게 동작합니다 (Contract Test 100% 통과)
- **SC-004**: 커서 기반 페이지네이션이 1만 개 이상의 결과에서도 일관되게 동작합니다
- **SC-005**: 동일 검색 조건의 두 번째 요청은 캐시 히트로 50ms 이내에 응답합니다

---

## API Design

### Endpoint

```
GET /recipes/search
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | No | 검색 키워드 (제목, 설명, 재료명, 요리사명) |
| `difficulty` | string | No | 난이도 필터 (easy, medium, hard) |
| `max_cook_time` | integer | No | 최대 조리시간 (분) |
| `tag` | string | No | 태그 필터 |
| `chef_id` | string (UUID) | No | 요리사 ID 필터 |
| `sort` | string | No | 정렬 기준 (relevance, latest, cook_time, popularity). 기본값: relevance |
| `cursor` | string | No | 페이지네이션 커서 |
| `limit` | integer | No | 결과 개수 (1-100, 기본값: 20) |

### Response Schema

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "김치찌개",
      "description": "맛있는 김치찌개",
      "thumbnail_url": "https://...",
      "prep_time_minutes": 10,
      "cook_time_minutes": 30,
      "difficulty": "easy",
      "exposure_score": 85.5,
      "chef": {
        "id": "uuid",
        "name": "백종원",
        "profile_image_url": "https://..."
      },
      "tags": [
        {"id": "uuid", "name": "한식", "category": "cuisine"}
      ],
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "next_cursor": "eyJzY29yZSI6...",
  "has_more": true,
  "total_count": null
}
```

### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_SEARCH_QUERY | 검색어가 너무 길거나 유효하지 않은 파라미터 |
| 400 | INVALID_SORT_OPTION | 유효하지 않은 정렬 옵션 |
| 400 | INVALID_FILTER_VALUE | 유효하지 않은 필터 값 (음수 조리시간 등) |

---

## Clarifications

**/speckit.clarify 실행 결과** (2025-12-10):

스펙 검토 결과, 구현에 필요한 모든 정보가 충분히 정의되어 있습니다. 다음 사항들이 명확화되었습니다:

### 확정된 구현 세부사항 (Phase 1 MVP)

1. **검색 알고리즘**: PostgreSQL ILIKE '%keyword%' 부분 일치 검색
   - 제목, 설명: 직접 ILIKE 검색
   - 재료명: RecipeIngredient.name JOIN 후 ILIKE
   - 요리사명: Chef.name JOIN 후 ILIKE
   - 여러 필드 중 하나라도 매칭되면 결과에 포함 (OR 조건)

2. **Relevance 정렬**: Phase 1에서는 `exposure_score DESC` 단순 정렬
   - 추후 Phase 2에서 Elasticsearch 연동 시 BM25 기반 스코어링

3. **태그 필터**: Phase 1은 단일 태그만 지원 (`tag=한식`)
   - 다중 태그 필터 (OR/AND)는 Phase 2에서 구현

4. **total_count**: 항상 `null` 반환 (성능 최적화)
   - 커서 기반 페이지네이션에서는 전체 개수 불필요
   - COUNT 쿼리 생략으로 성능 향상

5. **재료명 검색**: 부분 일치 (ILIKE '%keyword%')
   - RecipeIngredient.name 필드에서 검색

---

## Technical Notes

### Phase 1 (MVP - P1)
- PostgreSQL LIKE/ILIKE 기반 검색 구현
- 기본 필터링 및 정렬 지원
- 커서 기반 페이지네이션

### Phase 2 (Enhancement - P2/P3)
- Elasticsearch 연동으로 전문 검색 (Search Service 연동)
- 검색어 자동완성
- 형태소 분석 (한국어 nori 플러그인)
- 검색 결과 캐싱 (Redis)

### 의존성
- SPEC-004 완료 필요 (chefs 테이블, recipes 테이블)
- Search Service 연동은 Phase 2에서 구현
