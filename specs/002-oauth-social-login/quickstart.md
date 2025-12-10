# Quickstart: OAuth 소셜 로그인

## 통합 시나리오

### 시나리오 1: 카카오 신규 사용자 소셜 로그인

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        카카오 소셜 로그인 플로우                           │
└─────────────────────────────────────────────────────────────────────────┘

[Frontend]                [User Service]               [Kakao]              [Redis]
    │                          │                          │                    │
    │ GET /v1/auth/oauth/kakao │                          │                    │
    │─────────────────────────>│                          │                    │
    │                          │                          │                    │
    │                          │ SETEX oauth:state:{state} ─────────────────────>│
    │                          │                          │                    │
    │ {authorization_url, state}                          │                    │
    │<─────────────────────────│                          │                    │
    │                          │                          │                    │
    │ Redirect to kakao ───────────────────────────────────>│                    │
    │                          │                          │                    │
    │ User authenticates       │                          │                    │
    │<────────────────────────────────────────────────────│                    │
    │                          │                          │                    │
    │ POST /v1/auth/oauth/kakao/callback                  │                    │
    │ {code, state}            │                          │                    │
    │─────────────────────────>│                          │                    │
    │                          │                          │                    │
    │                          │ GET oauth:state:{state} <─────────────────────│
    │                          │ DEL oauth:state:{state} ─────────────────────>│
    │                          │                          │                    │
    │                          │ POST /oauth/token ────────>│                    │
    │                          │<─────── access_token ─────│                    │
    │                          │                          │                    │
    │                          │ GET /v2/user/me ──────────>│                    │
    │                          │<─────── user info ────────│                    │
    │                          │                          │                    │
    │                          │ [Create User + OAuthAccount in DB]            │
    │                          │                          │                    │
    │                          │ SETEX session:{user_id}  ─────────────────────>│
    │                          │                          │                    │
    │ 201 {access_token, refresh_token, user, is_new_user: true}               │
    │<─────────────────────────│                          │                    │
```

### 시나리오 2: 기존 이메일 사용자가 구글로 로그인 (계정 연동)

```
[사용자 상태]
- users 테이블: user@example.com으로 이메일 가입됨
- oauth_accounts 테이블: 연동된 소셜 계정 없음

[로그인 시도]
1. GET /v1/auth/oauth/google
   → authorization_url, state 반환

2. 사용자가 Google 인증 완료 (user@example.com)

3. POST /v1/auth/oauth/google/callback
   Body: {code: "...", state: "..."}

[서버 처리]
1. state 검증 (Redis 조회 → 삭제)
2. Google에서 access_token 획득
3. Google에서 사용자 정보 조회: email = user@example.com
4. OAuthAccount 조회: provider=google, provider_user_id=xxx → 없음
5. User 조회: email=user@example.com → 있음 (기존 이메일 사용자)
6. OAuthAccount 생성: user_id=기존user, provider=google
7. JWT 토큰 발급

[응답]
200 OK
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "기존 user ID",
    "email": "user@example.com",
    "provider": "google"
  },
  "is_new_user": false  // 기존 사용자이므로 false
}

[결과]
- users 테이블: 변경 없음
- oauth_accounts 테이블: 새 레코드 추가 (user_id, google, provider_user_id)
```

### 시나리오 3: 이미 연동된 소셜 계정으로 로그인

```
[사용자 상태]
- users 테이블: user@example.com (id: user-123)
- oauth_accounts 테이블: {user_id: user-123, provider: kakao, provider_user_id: kakao-456}

[로그인 시도]
1. 카카오 로그인 진행

[서버 처리]
1. state 검증
2. Kakao에서 access_token 획득
3. Kakao에서 사용자 정보 조회: provider_user_id = kakao-456
4. OAuthAccount 조회: provider=kakao, provider_user_id=kakao-456 → 있음!
5. 해당 OAuthAccount의 user_id로 User 조회
6. JWT 토큰 발급

[응답]
200 OK
{
  "access_token": "...",
  "refresh_token": "...",
  "is_new_user": false
}
```

## API 사용 예시

### 1. Authorization URL 요청

```bash
curl -X GET "http://localhost:8002/v1/auth/oauth/kakao"
```

**응답**:
```json
{
  "authorization_url": "https://kauth.kakao.com/oauth/authorize?client_id=xxx&redirect_uri=xxx&response_type=code&scope=profile_nickname%20account_email&state=abc123",
  "state": "abc123..."
}
```

### 2. OAuth 콜백 처리

```bash
curl -X POST "http://localhost:8002/v1/auth/oauth/kakao/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "authorization_code_from_kakao",
    "state": "abc123..."
  }'
```

**응답 (신규 사용자)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@kakao.com",
    "provider": "kakao",
    "created_at": "2025-12-10T10:00:00Z"
  },
  "is_new_user": true
}
```

## 에러 케이스

### State 만료/불일치

```bash
curl -X POST "http://localhost:8002/v1/auth/oauth/kakao/callback" \
  -H "Content-Type: application/json" \
  -d '{"code": "xxx", "state": "invalid_state"}'
```

**응답**:
```json
{
  "detail": "인증 요청이 만료되었습니다. 다시 시도해주세요",
  "error_code": "OAUTH_STATE_EXPIRED"
}
```

### 이메일 권한 거부

```json
{
  "detail": "이메일 정보가 필요합니다. 권한을 허용해주세요",
  "error_code": "OAUTH_EMAIL_REQUIRED"
}
```

### 지원하지 않는 제공자

```bash
curl -X GET "http://localhost:8002/v1/auth/oauth/apple"
```

**응답**:
```json
{
  "detail": "지원하지 않는 소셜 로그인입니다",
  "error_code": "OAUTH_UNSUPPORTED_PROVIDER"
}
```

## 환경 설정

### .env 파일

```bash
# 카카오
KAKAO_CLIENT_ID=your_kakao_app_key
KAKAO_CLIENT_SECRET=your_kakao_client_secret
KAKAO_REDIRECT_URI=http://localhost:3000/auth/callback/kakao

# 구글
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback/google

# 네이버
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
NAVER_REDIRECT_URI=http://localhost:3000/auth/callback/naver
```

### 제공자별 앱 등록

| 제공자 | 개발자 콘솔 | 필요 설정 |
|--------|------------|----------|
| 카카오 | https://developers.kakao.com | 플랫폼 등록, Redirect URI, 동의항목 |
| 구글 | https://console.cloud.google.com | OAuth 2.0 클라이언트 ID, Redirect URI |
| 네이버 | https://developers.naver.com | 애플리케이션 등록, API 권한, 콜백 URL |

## 테스트 방법

### 1. 단위 테스트

```bash
cd services/user-service
uv run pytest tests/unit/test_oauth_service.py -v
```

### 2. 통합 테스트 (Mock Provider)

```bash
uv run pytest tests/integration/test_oauth.py -v
```

### 3. 수동 테스트 (실제 제공자)

1. 환경 변수에 실제 OAuth 앱 정보 설정
2. 서버 실행: `uv run uvicorn user_service.main:app --reload --port 8002`
3. 브라우저에서 Authorization URL 접속
4. 소셜 로그인 진행
5. 콜백 URL에서 code, state 확인
6. POST 요청으로 토큰 발급 테스트
