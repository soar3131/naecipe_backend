# Feature Specification: 레시피북 기본 CRUD

**Feature Branch**: `007-cookbook-basic-crud`
**Created**: 2025-12-11
**Status**: Draft
**Input**: SPECKIT_TODO.md - SPEC-007: 레시피북 기본 CRUD

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 레시피북 생성 (Priority: P1) 🎯 MVP

사용자는 레시피를 분류하고 관리하기 위해 새로운 레시피북을 생성할 수 있습니다.
처음 레시피를 저장하려는 사용자에게 "내 레시피북"이 자동으로 생성됩니다.

**Why this priority**: 레시피 저장의 기본 컨테이너로, 모든 저장/피드백 기능의 전제 조건입니다.

**Independent Test**: `POST /api/v1/cookbooks` 호출로 레시피북 생성, 응답에서 생성된 ID 확인

**Acceptance Scenarios**:

1. **Given** 인증된 사용자가 레시피북이 없는 상태, **When** 첫 레시피 저장 시도 또는 레시피북 목록 조회, **Then** "내 레시피북"이 자동 생성됨
2. **Given** 인증된 사용자, **When** 이름(필수), 설명(선택), 커버 이미지(선택)로 레시피북 생성 요청, **Then** 레시피북이 생성되고 ID와 함께 응답
3. **Given** 인증된 사용자, **When** 이름이 비어있거나 100자 초과로 생성 요청, **Then** 400 Bad Request 반환
4. **Given** 미인증 사용자, **When** 레시피북 생성 요청, **Then** 401 Unauthorized 반환

---

### User Story 2 - 레시피북 목록 조회 (Priority: P1)

사용자는 자신의 모든 레시피북 목록을 조회하여 원하는 레시피북을 선택할 수 있습니다.

**Why this priority**: 레시피북 선택과 탐색의 기본 기능으로 MVP 필수 기능입니다.

**Independent Test**: `GET /api/v1/cookbooks` 호출로 레시피북 목록 조회, 정렬 순서 확인

**Acceptance Scenarios**:

1. **Given** 레시피북 3개를 가진 사용자, **When** 목록 조회 요청, **Then** 3개 레시피북이 sort_order 순으로 반환
2. **Given** 레시피북이 없는 사용자, **When** 목록 조회 요청, **Then** "내 레시피북" 자동 생성 후 1개 목록 반환
3. **Given** 각 레시피북에 저장된 레시피가 있는 경우, **When** 목록 조회, **Then** 각 레시피북의 saved_recipe_count 포함

---

### User Story 3 - 레시피북 상세 조회 (Priority: P2)

사용자는 특정 레시피북의 상세 정보를 조회할 수 있습니다.

**Why this priority**: 레시피북 관리와 수정을 위한 기본 정보 조회 기능입니다.

**Independent Test**: `GET /api/v1/cookbooks/{id}` 호출로 상세 정보 조회

**Acceptance Scenarios**:

1. **Given** 레시피북 ID, **When** 상세 조회 요청, **Then** 레시피북 정보 (이름, 설명, 커버 이미지, 생성일, 수정일, 저장된 레시피 수) 반환
2. **Given** 다른 사용자의 레시피북 ID, **When** 상세 조회 요청, **Then** 404 Not Found 반환 (권한 없음 숨김)
3. **Given** 존재하지 않는 레시피북 ID, **When** 상세 조회 요청, **Then** 404 Not Found 반환

---

### User Story 4 - 레시피북 수정 (Priority: P2)

사용자는 레시피북의 이름, 설명, 커버 이미지를 수정할 수 있습니다.

**Why this priority**: 레시피북 관리를 위한 기본 편집 기능입니다.

**Independent Test**: `PUT /api/v1/cookbooks/{id}` 호출로 레시피북 정보 수정

**Acceptance Scenarios**:

1. **Given** 기존 레시피북, **When** 이름만 수정 요청, **Then** 이름만 변경되고 나머지 유지
2. **Given** 기존 레시피북, **When** 설명과 커버 이미지 수정 요청, **Then** 해당 필드만 변경
3. **Given** "내 레시피북" (is_default=true), **When** 수정 요청, **Then** 정상적으로 수정 가능 (이름 변경 가능)
4. **Given** 다른 사용자의 레시피북, **When** 수정 요청, **Then** 404 Not Found 반환

---

### User Story 5 - 레시피북 삭제 (Priority: P3)

사용자는 더 이상 필요하지 않은 레시피북을 삭제할 수 있습니다.

**Why this priority**: 정리 기능으로 핵심 기능 완료 후 구현합니다.

**Independent Test**: `DELETE /api/v1/cookbooks/{id}` 호출로 레시피북 삭제

**Acceptance Scenarios**:

1. **Given** 저장된 레시피가 없는 레시피북, **When** 삭제 요청, **Then** 레시피북 삭제됨
2. **Given** 저장된 레시피가 있는 레시피북, **When** 삭제 요청, **Then** 레시피북과 저장된 레시피 연결 정보 함께 삭제
3. **Given** "내 레시피북" (is_default=true), **When** 삭제 요청, **Then** 400 Bad Request 반환 (기본 레시피북은 삭제 불가)
4. **Given** 사용자의 유일한 레시피북, **When** 삭제 요청 (기본 아닌 경우), **Then** 삭제 허용

---

### User Story 6 - 레시피북 순서 변경 (Priority: P3)

사용자는 레시피북의 표시 순서를 변경할 수 있습니다.

**Why this priority**: 사용자 편의 기능으로 핵심 기능 완료 후 구현합니다.

**Independent Test**: `PATCH /api/v1/cookbooks/reorder` 호출로 순서 변경

**Acceptance Scenarios**:

1. **Given** 레시피북 3개 (A=1, B=2, C=3), **When** 순서 변경 요청 [B, A, C], **Then** sort_order 업데이트 (B=1, A=2, C=3)
2. **Given** 레시피북 목록, **When** 일부 ID만 포함하여 순서 변경, **Then** 포함된 것만 순서 변경, 나머지는 유지
3. **Given** 다른 사용자의 레시피북 ID 포함, **When** 순서 변경 요청, **Then** 해당 ID 무시하고 본인 것만 처리

---

### Edge Cases

- **레시피북 이름 중복**: 동일 사용자가 같은 이름의 레시피북 생성 가능 (unique 제약 없음)
- **기본 레시피북 재생성**: 기본 레시피북 삭제 불가하므로 재생성 케이스 없음
- **동시성 처리**: 순서 변경 시 낙관적 잠금 불필요 (마지막 요청 우선)
- **이미지 URL 검증**: URL 형식 검증만, 실제 이미지 존재 여부는 검증하지 않음
- **대량 레시피북**: 사용자당 레시피북 최대 50개 제한 권장 (soft limit)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템 MUST 인증된 사용자의 첫 레시피북 조회/생성 시 "내 레시피북"을 자동 생성
- **FR-002**: 시스템 MUST 레시피북 생성 시 이름(1-100자)을 필수로 검증
- **FR-003**: 시스템 MUST 레시피북 목록을 sort_order 오름차순으로 반환
- **FR-004**: 시스템 MUST 레시피북 상세 조회 시 저장된 레시피 수 포함
- **FR-005**: 시스템 MUST 기본 레시피북(is_default=true) 삭제 요청 시 거부
- **FR-006**: 시스템 MUST 레시피북 삭제 시 관련 saved_recipes 레코드 삭제 (CASCADE)
- **FR-007**: 사용자 MUST 자신의 레시피북만 조회/수정/삭제 가능

### Key Entities

- **Cookbook (레시피북)**: 사용자의 레시피 컬렉션 컨테이너
  - 속성: id, user_id, name, description, cover_image_url, sort_order, is_default
  - 관계: User (N:1), SavedRecipe (1:N, 추후 SPEC-008에서 구현)

- **SavedRecipe (저장된 레시피)**: 레시피북에 저장된 레시피
  - 이 스펙에서는 cookbook 외래키 관계 및 카운트 집계만 고려
  - 상세 구현은 SPEC-008 (레시피 저장하기)에서 진행

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 레시피북 CRUD API 모든 엔드포인트 응답 시간 200ms 이내
- **SC-002**: 기본 레시피북 자동 생성이 첫 조회/저장 시 100% 동작
- **SC-003**: 레시피북 목록 조회 시 N+1 쿼리 없이 단일 쿼리로 처리
- **SC-004**: 모든 API에서 권한 검증 통과율 100% (타인 데이터 접근 차단)

## Technical Notes

### 의존성

- **선행 스펙**: SPEC-001 (사용자 인증) - JWT 토큰 기반 인증
- **후행 스펙**: SPEC-008 (레시피 저장하기) - SavedRecipe 테이블 상세 구현

### 모듈 배치

- `app/cookbooks/models.py`: Cookbook 모델
- `app/cookbooks/schemas.py`: Pydantic 스키마
- `app/cookbooks/services.py`: CookbookService 비즈니스 로직
- `app/cookbooks/router.py`: FastAPI 라우터
