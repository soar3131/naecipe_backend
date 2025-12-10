# Tasks: OAuth 소셜 로그인

**Branch**: `002-oauth-social-login` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Status**: ✅ Implementation Complete

---

## Phase 1: Setup (Foundational - All User Stories Depend on This)

- [x] T001 [Setup] `services/user-service/pyproject.toml` - httpx 의존성 추가 (OAuth HTTP 클라이언트)
- [x] T002 [Setup] `services/user-service/src/user_service/core/config.py` - OAuth 환경 변수 설정 추가 (KAKAO_CLIENT_ID, GOOGLE_CLIENT_ID, NAVER_CLIENT_ID 등)

---

## Phase 2: Data Layer (Foundational - User Stories Depend on This)

- [x] T003 [P] [Data] `services/user-service/src/user_service/models/oauth_account.py` - OAuthAccount SQLAlchemy 모델 생성 (data-model.md 참조)
- [x] T004 [Data] `services/user-service/src/user_service/models/__init__.py` - OAuthAccount 모델 export 추가
- [x] T005 [Data] `services/user-service/src/user_service/models/user.py` - oauth_accounts relationship 추가, password_hash nullable로 수정
- [x] T006 [Data] `services/user-service/alembic/versions/002_create_oauth_accounts.py` - 마이그레이션 생성 (oauth_accounts 테이블, users.password_hash nullable)

---

## Phase 3: Core Infrastructure (Foundational - All OAuth Endpoints Depend on This)

- [x] T007 [P] [Core] `services/user-service/src/user_service/schemas/oauth.py` - OAuth Pydantic 스키마 정의 (OAuthProvider, OAuthCallbackRequest, OAuthLoginResponse 등)
- [x] T008 [P] [Core] `services/user-service/src/user_service/core/oauth_providers.py` - 제공자별 설정 클래스 (카카오, 구글, 네이버 엔드포인트 및 스코프)
- [x] T009 [Core] 스킵 - Repository 대신 Service 패턴 사용 (기존 아키텍처 유지)

---

## Phase 4: User Story 1 & 2 - 카카오/구글 소셜 로그인 (P1)

- [x] T010 [US1,US2] `services/user-service/src/user_service/services/oauth.py` - OAuthService 클래스 구현:
  - generate_authorization_url() - Authorization URL 생성 및 state Redis 저장
  - handle_callback() - 콜백 처리, 토큰 교환, 사용자 정보 조회
  - _exchange_code_for_token() - authorization code를 access token으로 교환
  - _get_user_info() - 제공자로부터 사용자 정보 조회
  - _find_or_create_user() - 사용자 조회 또는 생성
  - link_account() - 기존 사용자에 OAuth 계정 연동
- [x] T011 [US1,US2] `services/user-service/src/user_service/api/v1/oauth.py` - OAuth 라우터 구현:
  - GET /v1/auth/oauth/{provider} - Authorization URL 반환
  - POST /v1/auth/oauth/{provider}/callback - 콜백 처리, JWT 발급
  - POST /v1/auth/oauth/{provider}/link - 계정 연동
- [x] T012 [US1,US2] `services/user-service/src/user_service/api/v1/router.py` - OAuth 라우터 등록
- [x] T013 [US1,US2] `services/user-service/src/user_service/core/exceptions.py` - OAuth 관련 예외 추가 (OAuthStateError, OAuthProviderError, OAuthAccountAlreadyLinkedError, UnsupportedOAuthProviderError)

---

## Phase 5: User Story 3 - 네이버 소셜 로그인 (P2)

- [x] T014 [US3] `services/user-service/src/user_service/core/oauth_providers.py` - 네이버 제공자 설정 추가 (엔드포인트, 응답 파싱 로직)
- [x] T015 [US3] `services/user-service/src/user_service/core/oauth_providers.py` - 네이버 응답 파싱 로직 추가 (response 객체 내부 데이터 추출) - parse_user_info() 함수

---

## Phase 6: User Story 4 - 기존 계정 연동 (P2)

- [x] T016 [US4] `services/user-service/src/user_service/services/oauth.py` - 이메일 기반 계정 연동 로직:
  - 이메일로 기존 User 조회
  - 있으면 OAuthAccount만 생성하여 연동
  - is_new_user 플래그 설정

---

## Phase 7: Testing

- [x] T017 [P] [Test] `services/user-service/tests/unit/test_oauth_service.py` - OAuthService 단위 테스트:
  - Authorization URL 생성 테스트
  - state 토큰 생성/검증 테스트
  - 사용자 정보 파싱 테스트 (제공자별)
- [x] T018 [P] [Test] `services/user-service/tests/contract/test_oauth.py` - OAuth Contract 테스트:
  - Authorization URL 응답 스키마 테스트
  - Callback 요청 검증 테스트
  - 에러 응답 RFC 7807 형식 테스트

---

## Phase 8: Polish (Common Concerns)

- [ ] T019 [Polish] 마이그레이션 실행 및 검증 (DB 환경 필요)
- [x] T020 [Polish] API 문서 자동 생성 확인 (Swagger UI) - FastAPI 자동 생성
- [x] T021 [Polish] `.env.example` 업데이트 (OAuth 환경 변수 추가)

---

## Task Dependencies

```
T001, T002 (Setup)
    ↓
T003, T004, T005, T006 (Data Layer)
    ↓
T007, T008, T009 (Core Infrastructure)
    ↓
T010, T011, T012, T013 (US1, US2 - P1)
    ↓
T014, T015 (US3 - P2)
    ↓
T016 (US4 - P2)
    ↓
T017, T018 (Testing)
    ↓
T019, T020, T021 (Polish)
```

## Legend

- `[P]` = Parallelizable (can run concurrently with other [P] tasks in same phase)
- `[US#]` = Maps to User Story number
- `[Setup]` = Project setup task
- `[Data]` = Data layer task
- `[Core]` = Core infrastructure task
- `[Test]` = Testing task
- `[Polish]` = Final polish task
