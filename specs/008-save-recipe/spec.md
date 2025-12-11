# Feature Specification: 레시피 저장 (원본 레시피 → 레시피북)

**Feature Branch**: `008-save-recipe`
**Created**: 2025-12-11
**Status**: Draft
**Input**: User description: "원본 레시피를 레시피북에 저장하고, 개인 메모를 추가/수정하며, 저장된 레시피를 관리하는 기능"

## User Scenarios & Testing *(mandatory)*

<!--
  레시피 저장 기능은 사용자가 원본 레시피를 자신의 레시피북에 저장하고 관리할 수 있게 합니다.
  각 유저 스토리는 독립적으로 테스트 가능하며, MVP 증분으로 구현됩니다.
-->

### User Story 1 - 원본 레시피 저장 (Priority: P1) 🎯 MVP

사용자가 레시피 검색/조회 후 마음에 드는 원본 레시피를 자신의 레시피북에 저장할 수 있다. 저장 시 선택적으로 개인 메모를 추가할 수 있다.

**Why this priority**: 레시피 저장은 서비스의 핵심 기능으로, 사용자가 레시피를 수집하고 개인화하는 첫 단계입니다. 이 기능 없이는 이후의 보정 레시피, 조리 피드백 등의 기능을 사용할 수 없습니다.

**Independent Test**: `POST /api/v1/cookbooks/{id}/recipes` API를 호출하여 레시피가 레시피북에 저장되고, 저장된 레시피 ID가 반환되는지 확인

**Acceptance Scenarios**:

1. **Given** 인증된 사용자가 레시피북과 원본 레시피가 있을 때, **When** recipe_id와 함께 저장 요청을 보내면, **Then** SavedRecipe가 생성되고 201 응답과 함께 저장된 레시피 정보가 반환된다
2. **Given** 인증된 사용자가 저장 요청 시, **When** 메모(memo)를 함께 전송하면, **Then** 메모가 포함된 SavedRecipe가 생성된다
3. **Given** 인증된 사용자가 저장 요청 시, **When** 메모를 생략하면, **Then** 메모가 null인 SavedRecipe가 생성된다
4. **Given** 인증된 사용자가 저장 요청 시, **When** 동일한 레시피를 같은 레시피북에 중복 저장하려고 하면, **Then** 409 Conflict 응답이 반환된다
5. **Given** 인증된 사용자가 저장 요청 시, **When** 존재하지 않는 recipe_id를 전송하면, **Then** 404 Not Found 응답이 반환된다
6. **Given** 인증된 사용자가 저장 요청 시, **When** 다른 사용자의 레시피북에 저장하려고 하면, **Then** 404 Not Found 응답이 반환된다 (권한 없음을 숨김)

---

### User Story 2 - 저장된 레시피 목록 조회 (Priority: P1) 🎯 MVP

사용자가 레시피북에 저장된 레시피 목록을 조회할 수 있다. 목록에는 원본 레시피 정보와 저장 메타데이터가 포함된다.

**Why this priority**: 저장 기능과 함께 필수적인 기능으로, 사용자가 저장한 레시피를 확인하고 탐색할 수 있어야 합니다.

**Independent Test**: `GET /api/v1/cookbooks/{id}/recipes` API를 호출하여 저장된 레시피 목록이 반환되는지 확인

**Acceptance Scenarios**:

1. **Given** 레시피가 저장된 레시피북이 있을 때, **When** 목록 조회 요청을 보내면, **Then** 저장된 레시피 목록이 페이지네이션과 함께 반환된다
2. **Given** 저장된 레시피가 있을 때, **When** 목록을 조회하면, **Then** 각 항목에 원본 레시피 요약 정보(title, thumbnail), 메모, 저장일시가 포함된다
3. **Given** 저장된 레시피가 없는 레시피북일 때, **When** 목록을 조회하면, **Then** 빈 목록이 반환된다
4. **Given** 레시피북이 존재할 때, **When** 다른 사용자가 조회하면, **Then** 404 Not Found 응답이 반환된다

---

### User Story 3 - 저장된 레시피 상세 조회 (Priority: P2)

사용자가 저장된 레시피의 상세 정보를 조회할 수 있다. 원본 레시피 전체 정보와 저장 메타데이터를 함께 확인할 수 있다.

**Why this priority**: 저장 후 상세 정보 확인은 자연스러운 다음 단계이며, 이후 조리 및 피드백 기능과 연결됩니다.

**Independent Test**: `GET /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` API를 호출하여 상세 정보가 반환되는지 확인

**Acceptance Scenarios**:

1. **Given** 저장된 레시피가 있을 때, **When** 상세 조회 요청을 보내면, **Then** 원본 레시피 전체 정보와 저장 메타데이터가 반환된다
2. **Given** 저장된 레시피가 있을 때, **When** 상세를 조회하면, **Then** memo, cook_count, personal_rating, last_cooked_at 정보가 포함된다
3. **Given** 존재하지 않는 savedRecipeId로 조회할 때, **When** 요청을 보내면, **Then** 404 Not Found 응답이 반환된다
4. **Given** 다른 사용자의 저장된 레시피일 때, **When** 조회하면, **Then** 404 Not Found 응답이 반환된다

---

### User Story 4 - 저장된 레시피 메모 수정 (Priority: P2)

사용자가 저장된 레시피의 개인 메모를 수정할 수 있다.

**Why this priority**: 메모 수정은 개인화의 핵심이지만, 저장/조회보다는 부가적인 기능입니다.

**Independent Test**: `PUT /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` API를 호출하여 메모가 업데이트되는지 확인

**Acceptance Scenarios**:

1. **Given** 저장된 레시피가 있을 때, **When** 메모 수정 요청을 보내면, **Then** 메모가 업데이트되고 수정된 정보가 반환된다
2. **Given** 저장된 레시피가 있을 때, **When** 빈 문자열로 메모를 수정하면, **Then** 메모가 빈 문자열로 저장된다
3. **Given** 저장된 레시피가 있을 때, **When** null로 메모를 수정하면, **Then** 메모가 null로 저장된다
4. **Given** 다른 사용자의 저장된 레시피일 때, **When** 수정하려고 하면, **Then** 404 Not Found 응답이 반환된다

---

### User Story 5 - 저장된 레시피 삭제 (Priority: P3)

사용자가 저장된 레시피를 삭제할 수 있다. 삭제 시 관련된 보정 레시피(RecipeVariation)도 함께 삭제된다.

**Why this priority**: 삭제는 중요하지만 저장/조회/수정보다 사용 빈도가 낮습니다.

**Independent Test**: `DELETE /api/v1/cookbooks/{cookbookId}/recipes/{savedRecipeId}` API를 호출하여 저장된 레시피가 삭제되는지 확인

**Acceptance Scenarios**:

1. **Given** 저장된 레시피가 있을 때, **When** 삭제 요청을 보내면, **Then** 저장된 레시피가 삭제되고 204 No Content 응답이 반환된다
2. **Given** 저장된 레시피에 보정 레시피(RecipeVariation)가 연결되어 있을 때, **When** 삭제하면, **Then** 보정 레시피도 함께 삭제된다 (cascade)
3. **Given** 존재하지 않는 savedRecipeId로 삭제할 때, **When** 요청을 보내면, **Then** 404 Not Found 응답이 반환된다
4. **Given** 다른 사용자의 저장된 레시피일 때, **When** 삭제하려고 하면, **Then** 404 Not Found 응답이 반환된다

---

### Edge Cases

- 원본 레시피가 삭제된 경우: 저장된 레시피는 유지하되, 원본 정보 조회 시 삭제됨 표시 또는 null 처리
- 레시피북이 삭제된 경우: CASCADE로 해당 레시피북의 모든 저장된 레시피도 삭제
- 메모 최대 길이: 1000자 제한
- 동시 저장 요청: 유니크 제약으로 중복 방지 (cookbook_id + original_recipe_id)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST 원본 레시피를 레시피북에 저장할 수 있다 (참조 방식, 복사 아님)
- **FR-002**: System MUST 저장 시 선택적으로 개인 메모를 추가할 수 있다
- **FR-003**: System MUST 동일 레시피북에 같은 레시피 중복 저장을 방지한다 (UNIQUE 제약)
- **FR-004**: System MUST 저장된 레시피 목록을 페이지네이션하여 조회할 수 있다
- **FR-005**: System MUST 저장된 레시피의 상세 정보를 조회할 수 있다
- **FR-006**: System MUST 저장된 레시피의 메모를 수정할 수 있다
- **FR-007**: System MUST 저장된 레시피를 삭제할 수 있다
- **FR-008**: System MUST 저장된 레시피 삭제 시 관련 보정 레시피(RecipeVariation)도 CASCADE 삭제한다
- **FR-009**: System MUST 다른 사용자의 레시피북/저장된 레시피에 대한 접근을 차단한다

### Key Entities

- **SavedRecipe**: 사용자가 레시피북에 저장한 원본 레시피에 대한 참조
  - cookbook_id: 소속 레시피북 (FK → cookbooks)
  - original_recipe_id: 원본 레시피 참조 (FK → recipes)
  - active_version_id: 현재 활성 보정 레시피 버전 (nullable, FK → recipe_variations)
  - memo: 개인 메모 (nullable, max 1000자)
  - cook_count: 조리 횟수 (기본값 0, 향후 피드백 기능에서 증가)
  - personal_rating: 개인 평점 (nullable, 향후 피드백 기능에서 설정)
  - last_cooked_at: 마지막 조리 일시 (nullable)
  - created_at, updated_at: 생성/수정 시각

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자가 레시피 저장을 500ms 이내에 완료할 수 있다
- **SC-002**: 저장된 레시피 목록 조회가 200ms 이내에 완료된다 (페이지당 20개 기준)
- **SC-003**: 중복 저장 시도 시 즉시 명확한 오류 메시지가 반환된다
- **SC-004**: 삭제 시 관련 보정 레시피가 100% CASCADE 삭제된다

## Dependencies

### 선행 스펙

- **SPEC-007**: 레시피북 기본 CRUD (Cookbook 모델, 서비스) ✅ 완료
- **SPEC-004**: 원본 레시피 기본 CRUD (Recipe 모델) ✅ 완료

### 후행 스펙

- **SPEC-009**: AI 레시피 보정 (RecipeVariation 생성)
- **SPEC-010**: 조리 피드백 (cook_count, personal_rating, last_cooked_at 업데이트)
