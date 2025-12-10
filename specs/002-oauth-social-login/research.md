# Research: OAuth 소셜 로그인

**Feature**: 002-oauth-social-login
**Date**: 2025-12-10

## OAuth 제공자별 구현 방식

### Decision 1: OAuth 라이브러리 선택

**Decision**: `httpx` + 직접 구현

**Rationale**:
- Constitution VII (Simplicity) 원칙 준수: 불필요한 추상화 레이어 최소화
- 각 제공자(카카오, 구글, 네이버)의 OAuth 엔드포인트가 표준화되어 있음
- authlib, python-social-auth 등은 과도한 기능 제공
- httpx는 이미 SPEC-001에서 사용 중 (의존성 추가 없음)

**Alternatives Considered**:
| 라이브러리 | 장점 | 단점 |
|-----------|------|------|
| authlib | 표준 준수, 다양한 제공자 | 복잡한 API, 과도한 추상화 |
| python-social-auth | Django 통합 우수 | FastAPI 지원 미흡, 의존성 과다 |
| httpx + 직접 구현 | 단순, 제어 가능, 의존성 최소 | 직접 구현 필요 |

---

### Decision 2: OAuth State 관리

**Decision**: Redis에 state 토큰 저장 (TTL 10분)

**Rationale**:
- CSRF 공격 방지를 위해 state 파라미터 필수
- 세션 쿠키 대신 Redis 사용으로 stateless 서버 유지
- TTL 10분: OAuth 플로우 완료에 충분한 시간
- SPEC-001에서 이미 Redis 연결 구성됨

**Implementation**:
```python
# OAuth 시작 시
state = secrets.token_urlsafe(32)
await redis.setex(f"oauth:state:{state}", 600, provider)  # TTL 600초

# 콜백 시
provider = await redis.get(f"oauth:state:{state}")
if not provider:
    raise InvalidStateError()
await redis.delete(f"oauth:state:{state}")
```

---

### Decision 3: 제공자별 엔드포인트

**Decision**: 제공자별 공식 OAuth2.0 엔드포인트 사용

#### 카카오 (Kakao)

| 구분 | 엔드포인트 |
|------|-----------|
| Authorization | `https://kauth.kakao.com/oauth/authorize` |
| Token | `https://kauth.kakao.com/oauth/token` |
| User Info | `https://kapi.kakao.com/v2/user/me` |
| Scopes | `profile_nickname`, `profile_image`, `account_email` |

**특이사항**:
- 이메일 권한은 앱 검수 후 사용 가능 (개발 단계에서는 팀원만)
- 응답에서 `kakao_account.email` 위치 확인 필요

#### 구글 (Google)

| 구분 | 엔드포인트 |
|------|-----------|
| Authorization | `https://accounts.google.com/o/oauth2/v2/auth` |
| Token | `https://oauth2.googleapis.com/token` |
| User Info | `https://www.googleapis.com/oauth2/v2/userinfo` |
| Scopes | `openid`, `email`, `profile` |

**특이사항**:
- OpenID Connect 지원, id_token에서 정보 추출 가능
- 표준적인 OAuth2.0 구현

#### 네이버 (Naver)

| 구분 | 엔드포인트 |
|------|-----------|
| Authorization | `https://nid.naver.com/oauth2.0/authorize` |
| Token | `https://nid.naver.com/oauth2.0/token` |
| User Info | `https://openapi.naver.com/v1/nid/me` |
| Scopes | (기본 프로필만 제공) |

**특이사항**:
- 응답 구조가 `response` 객체 안에 데이터 포함
- 이메일은 사용자가 공개 설정한 경우에만 제공

---

### Decision 4: 계정 연동 전략

**Decision**: 이메일 기준 자동 연동

**Rationale**:
- 동일 이메일 = 동일 사용자로 간주 (업계 표준)
- 사용자 경험 우선: 추가 인증 단계 없이 연동
- 보안 고려: 이메일은 소셜 제공자에서 검증된 것으로 신뢰

**Flow**:
```
1. 소셜 로그인 시도
2. 소셜 제공자에서 이메일 조회
3. 기존 사용자 조회 (email 기준)
   - 있음 → oauth_accounts에 연동 추가, 기존 user_id로 로그인
   - 없음 → 신규 User 생성, oauth_accounts 추가
4. JWT 토큰 발급 (기존 로직 재사용)
```

---

### Decision 5: 소셜 토큰 저장

**Decision**: OAuth access_token/refresh_token은 DB에 저장하지 않음

**Rationale**:
- 현재 요구사항에서 소셜 API 추가 호출 불필요
- 토큰 저장은 보안 리스크 증가 (민감 데이터)
- 필요 시 SPEC-003에서 확장 가능

**저장하는 정보**:
- provider (kakao, google, naver)
- provider_user_id (제공자별 사용자 ID)
- provider_email (연동 시점의 이메일)
- created_at, updated_at

---

### Decision 6: API 설계

**Decision**: Authorization URL 생성과 콜백 처리를 분리

**Endpoints**:

| Method | Path | 설명 |
|--------|------|------|
| GET | `/v1/auth/oauth/{provider}` | Authorization URL 반환 |
| POST | `/v1/auth/oauth/{provider}/callback` | 콜백 처리, 토큰 발급 |

**Rationale**:
- 프론트엔드에서 Authorization URL을 받아 리다이렉트 처리
- 콜백은 POST로 처리하여 authorization code를 body로 전달
- SPECKIT_TODO.md의 `POST /auth/oauth/:provider` 패턴과 일치

---

## 환경 변수 설정

```bash
# 카카오
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=

# 구글
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=

# 네이버
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_REDIRECT_URI=
```

---

## 에러 처리 전략

| 에러 상황 | HTTP 코드 | 메시지 |
|----------|----------|--------|
| 유효하지 않은 provider | 400 | "지원하지 않는 소셜 로그인입니다" |
| state 검증 실패 | 400 | "인증 요청이 만료되었습니다. 다시 시도해주세요" |
| 이메일 권한 거부 | 400 | "이메일 정보가 필요합니다. 권한을 허용해주세요" |
| 소셜 제공자 오류 | 502 | "소셜 로그인 서버에 문제가 발생했습니다" |
| 토큰 교환 실패 | 400 | "인증에 실패했습니다. 다시 시도해주세요" |

---

## 테스트 전략

### 단위 테스트
- OAuth URL 생성 로직
- State 토큰 생성/검증
- 사용자 정보 파싱 (제공자별)
- 계정 연동 로직

### 통합 테스트
- Mock OAuth 서버로 전체 플로우 테스트
- Redis state 저장/조회
- DB 트랜잭션 (User + OAuthAccount 생성)
- JWT 토큰 발급 연동

### E2E 테스트 (수동)
- 실제 소셜 제공자 연동 확인 (Staging 환경)
