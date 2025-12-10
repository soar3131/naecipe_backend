# Feature Specification: 사용자 인증 기본

**Feature Branch**: `001-user-auth`
**Created**: 2025-12-10
**Status**: Draft
**Input**: SPEC-001: 사용자 인증 기본 - 이메일 회원가입/로그인, JWT 토큰 발급, 비밀번호 해싱, 세션 관리

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 이메일 회원가입 (Priority: P1)

신규 사용자가 이메일과 비밀번호로 계정을 생성한다. 레시피 앱을 사용하려면 먼저 계정이 있어야 하므로 가장 기본적인 기능이다.

**Why this priority**: 계정 생성 없이는 어떤 서비스도 이용할 수 없다. 모든 사용자 여정의 시작점.

**Independent Test**: 이메일과 비밀번호를 입력하여 계정을 생성하고, 생성된 계정으로 로그인할 수 있다.

**Acceptance Scenarios**:

1. **Given** 가입하지 않은 이메일 주소, **When** 유효한 이메일과 비밀번호로 회원가입 요청, **Then** 계정이 생성되고 성공 응답을 받는다
2. **Given** 이미 가입된 이메일 주소, **When** 같은 이메일로 회원가입 요청, **Then** 이메일 중복 오류 응답을 받는다
3. **Given** 잘못된 형식의 이메일, **When** 회원가입 요청, **Then** 유효성 검사 오류 응답을 받는다
4. **Given** 정책에 맞지 않는 비밀번호(예: 너무 짧음), **When** 회원가입 요청, **Then** 비밀번호 정책 오류 응답을 받는다

---

### User Story 2 - 로그인 및 토큰 발급 (Priority: P1)

등록된 사용자가 이메일과 비밀번호로 로그인하여 인증 토큰을 받는다. 토큰을 사용해 보호된 API에 접근한다.

**Why this priority**: 회원가입과 함께 가장 기본적인 인증 기능. 다른 모든 보호된 기능에 접근하기 위한 전제 조건.

**Independent Test**: 올바른 자격 증명으로 로그인하고, 발급받은 토큰으로 보호된 엔드포인트에 접근할 수 있다.

**Acceptance Scenarios**:

1. **Given** 등록된 사용자, **When** 올바른 이메일과 비밀번호로 로그인, **Then** Access Token과 Refresh Token을 발급받는다
2. **Given** 등록된 사용자, **When** 잘못된 비밀번호로 로그인, **Then** 인증 실패 오류를 받는다
3. **Given** 미등록 이메일, **When** 로그인 시도, **Then** 인증 실패 오류를 받는다
4. **Given** 유효한 Access Token, **When** 보호된 API 호출, **Then** 정상적으로 응답을 받는다
5. **Given** 만료되거나 유효하지 않은 토큰, **When** 보호된 API 호출, **Then** 인증 필요 오류를 받는다

---

### User Story 3 - 토큰 갱신 (Priority: P2)

사용자가 만료된 Access Token을 Refresh Token으로 갱신하여 재로그인 없이 서비스를 계속 이용한다.

**Why this priority**: 사용자 경험 향상을 위한 필수 기능이나, 회원가입/로그인 후에 구현해도 무방.

**Independent Test**: Access Token 만료 후 Refresh Token으로 새 Access Token을 발급받을 수 있다.

**Acceptance Scenarios**:

1. **Given** 유효한 Refresh Token, **When** 토큰 갱신 요청, **Then** 새로운 Access Token과 Refresh Token을 받는다
2. **Given** 만료된 Refresh Token, **When** 토큰 갱신 요청, **Then** 인증 오류를 받고 재로그인이 필요하다
3. **Given** 잘못된 Refresh Token, **When** 토큰 갱신 요청, **Then** 인증 오류를 받는다

---

### User Story 4 - 로그아웃 (Priority: P2)

사용자가 로그아웃하여 현재 세션을 종료하고 발급된 토큰을 무효화한다.

**Why this priority**: 보안상 필요하지만 MVP로는 토큰 만료에 의존할 수도 있음.

**Independent Test**: 로그아웃 후 이전에 발급받은 토큰으로 API에 접근할 수 없다.

**Acceptance Scenarios**:

1. **Given** 로그인된 사용자, **When** 로그아웃 요청, **Then** 성공 응답을 받고 현재 토큰이 무효화된다
2. **Given** 로그아웃한 사용자, **When** 이전 Access Token으로 API 호출, **Then** 인증 필요 오류를 받는다
3. **Given** 로그아웃한 사용자, **When** 이전 Refresh Token으로 갱신 시도, **Then** 인증 오류를 받는다

---

### Edge Cases

- 동시에 여러 기기에서 로그인 시 각 기기마다 독립적인 세션이 유지되어야 한다
- 비밀번호 입력 연속 실패 시 계정 잠금 또는 지연 적용 (무차별 대입 공격 방지)
- 매우 긴 이메일이나 비밀번호 입력 시 적절히 거부해야 한다
- 네트워크 오류로 인해 토큰 갱신이 실패했을 때 클라이언트가 재시도할 수 있어야 한다

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 이메일과 비밀번호로 신규 사용자 계정을 생성할 수 있어야 한다
- **FR-002**: 시스템은 이메일 형식을 검증하고, 중복된 이메일은 거부해야 한다
- **FR-003**: 시스템은 비밀번호를 안전하게 해싱하여 저장해야 한다 (평문 저장 금지)
- **FR-004**: 시스템은 비밀번호 정책을 적용해야 한다 (최소 8자, 영문+숫자 포함)
- **FR-005**: 시스템은 올바른 자격 증명으로 로그인 시 Access Token과 Refresh Token을 발급해야 한다
- **FR-006**: Access Token은 짧은 유효기간(15분), Refresh Token은 긴 유효기간(7일)을 가져야 한다
- **FR-007**: 시스템은 Refresh Token을 사용해 새로운 Access Token을 발급할 수 있어야 한다
- **FR-008**: 시스템은 세션 정보를 저장하고 토큰 무효화를 지원해야 한다
- **FR-009**: 시스템은 로그아웃 시 해당 세션의 Refresh Token을 무효화해야 한다
- **FR-010**: 시스템은 보호된 엔드포인트 접근 시 유효한 Access Token을 검증해야 한다
- **FR-011**: 연속 로그인 실패(5회) 시 계정을 일시적으로 잠금(15분)해야 한다

### Key Entities

- **User**: 시스템 사용자를 나타냄. 이메일(고유), 해싱된 비밀번호, 생성일, 상태(활성/비활성/잠금) 속성 포함
- **Session**: 사용자의 로그인 세션. 사용자 ID, Refresh Token, 생성 시각, 만료 시각, 기기 정보 포함. 로그아웃 시 삭제됨

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 사용자는 30초 이내에 회원가입을 완료할 수 있다
- **SC-002**: 사용자는 5초 이내에 로그인하고 토큰을 받을 수 있다
- **SC-003**: 토큰 갱신은 1초 이내에 완료된다
- **SC-004**: 시스템은 1,000명의 동시 로그인 요청을 처리할 수 있다
- **SC-005**: 인증 실패 시 명확한 오류 메시지를 제공하여 사용자가 문제를 이해할 수 있다
- **SC-006**: 로그아웃한 토큰으로의 접근 시도는 100% 차단된다

## Assumptions

- OAuth 소셜 로그인은 SPEC-002에서 별도로 다룸
- 사용자 프로필 및 취향 설정은 SPEC-003에서 별도로 다룸
- 비밀번호 재설정(찾기) 기능은 이 스펙 범위에 포함되지 않음 (추후 별도 스펙)
- 이메일 인증(가입 시 이메일 확인)은 MVP에서 제외 (추후 별도 스펙)
- 다중 기기 로그인을 지원하며, 각 기기별 독립 세션 유지

## Scope Boundaries

### 포함 (In Scope)

- 이메일/비밀번호 기반 회원가입
- 이메일/비밀번호 기반 로그인
- JWT Access Token + Refresh Token 발급
- 비밀번호 해싱 (bcrypt)
- 세션 관리 및 토큰 무효화
- 로그아웃
- 계정 잠금 (연속 실패 시)

### 제외 (Out of Scope)

- OAuth 소셜 로그인 (SPEC-002)
- 사용자 프로필 조회/수정 (SPEC-003)
- 취향/식이제한 설정 (SPEC-003)
- 비밀번호 재설정
- 이메일 인증
- 2단계 인증 (2FA)
- 회원 탈퇴
