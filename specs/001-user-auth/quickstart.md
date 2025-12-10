# Quickstart: 사용자 인증 기본

**Feature Branch**: `001-user-auth`
**Date**: 2025-12-10

이 문서는 사용자 인증 기능의 통합 시나리오를 설명합니다.

---

## 1. 사전 요구사항

### 서비스 의존성
```bash
# Docker Compose로 인프라 실행
docker-compose up -d postgres redis
```

### 환경 변수
```bash
# .env
DATABASE_URL=postgresql+asyncpg://naecipe:password@localhost:5432/naecipe_user
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 2. 통합 시나리오

### 시나리오 1: 회원가입 → 로그인 → API 접근

```bash
# 1. 회원가입
curl -X POST http://localhost:8002/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'

# 응답: 201 Created
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2025-12-10T09:00:00Z"
}
```

```bash
# 2. 로그인
curl -X POST http://localhost:8002/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123"
  }'

# 응답: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

```bash
# 3. 보호된 API 접근
curl -X GET http://localhost:8002/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 응답: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "status": "active",
  "created_at": "2025-12-10T09:00:00Z"
}
```

---

### 시나리오 2: 토큰 갱신

```bash
# Access Token 만료 후 Refresh Token으로 갱신
curl -X POST http://localhost:8002/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'

# 응답: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...(새 토큰)",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...(새 토큰)",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### 시나리오 3: 로그아웃

```bash
# 로그아웃 (Access Token 필요)
curl -X POST http://localhost:8002/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 응답: 204 No Content
```

```bash
# 로그아웃 후 이전 토큰으로 API 호출 시도
curl -X GET http://localhost:8002/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 응답: 401 Unauthorized
{
  "type": "https://api.naecipe.com/errors/auth/token-revoked",
  "title": "Token Revoked",
  "status": 401,
  "detail": "토큰이 무효화되었습니다. 다시 로그인해주세요.",
  "instance": "/v1/auth/me"
}
```

---

### 시나리오 4: 계정 잠금

```bash
# 5회 연속 잘못된 비밀번호로 로그인 시도 후
curl -X POST http://localhost:8002/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "wrong-password"
  }'

# 응답: 423 Locked
{
  "type": "https://api.naecipe.com/errors/auth/account-locked",
  "title": "Account Locked",
  "status": 423,
  "detail": "연속된 로그인 실패로 계정이 잠겼습니다. 15분 후 다시 시도해주세요.",
  "instance": "/v1/auth/login"
}
```

---

## 3. 에러 응답 패턴

### 입력 유효성 검사 실패 (400)
```json
{
  "type": "https://api.naecipe.com/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "비밀번호는 최소 8자 이상이어야 합니다.",
  "instance": "/v1/auth/register"
}
```

### 인증 실패 (401)
```json
{
  "type": "https://api.naecipe.com/errors/auth/invalid-credentials",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "이메일 또는 비밀번호가 올바르지 않습니다.",
  "instance": "/v1/auth/login"
}
```

### 이메일 중복 (409)
```json
{
  "type": "https://api.naecipe.com/errors/auth/email-exists",
  "title": "Email Already Exists",
  "status": 409,
  "detail": "이미 등록된 이메일 주소입니다.",
  "instance": "/v1/auth/register"
}
```

---

## 4. 다른 서비스에서의 토큰 검증

다른 마이크로서비스(recipe-service, cookbook-service 등)에서 User Service의 토큰을 검증하는 방법:

### 옵션 A: JWT 직접 검증 (권장)

```python
# shared/utils/auth.py
from jose import jwt, JWTError
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다."
        )
```

### 옵션 B: gRPC로 User Service 호출 (토큰 무효화 확인 필요 시)

```protobuf
// shared/proto/user.proto
service UserService {
  rpc ValidateToken(ValidateTokenRequest) returns (ValidateTokenResponse);
}

message ValidateTokenRequest {
  string access_token = 1;
}

message ValidateTokenResponse {
  bool valid = 1;
  string user_id = 2;
  string email = 3;
}
```

---

## 5. 테스트 실행

```bash
# User Service 디렉토리에서
cd services/user-service

# 단위 테스트
pytest tests/unit/ -v

# 통합 테스트 (PostgreSQL, Redis 필요)
pytest tests/integration/ -v

# Contract 테스트
pytest tests/contract/ -v

# 전체 테스트
pytest tests/ -v --cov=src --cov-report=html
```

---

## 6. Health Check

```bash
# 서비스 상태 확인
curl http://localhost:8002/health

# 응답
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "database": "ok",
    "redis": "ok"
  }
}
```

```bash
# Readiness 확인 (Kubernetes 용)
curl http://localhost:8002/ready

# 응답: 200 OK (준비 완료) 또는 503 Service Unavailable (준비 중)
```
