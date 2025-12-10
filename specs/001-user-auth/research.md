# Research: 사용자 인증 기본

**Feature Branch**: `001-user-auth`
**Date**: 2025-12-10

## 1. JWT 라이브러리 선택

### Decision: PyJWT + python-jose

### Rationale
- **PyJWT**: 가장 널리 사용되는 JWT 라이브러리, 간단한 API
- **python-jose**: FastAPI 공식 문서에서 권장, JOSE 표준 지원
- FastAPI Security 모듈과의 통합이 잘 되어 있음

### Alternatives Considered
- **authlib**: 기능이 풍부하나 OAuth 중심 설계, SPEC-001 범위에서는 오버엔지니어링
- **PyJWT 단독**: 기본 기능 충분하나 python-jose가 더 나은 알고리즘 지원

---

## 2. 비밀번호 해싱 알고리즘

### Decision: bcrypt (passlib)

### Rationale
- **bcrypt**: 업계 표준, 시간 지연 공격 방지, 솔트 자동 생성
- **passlib**: 여러 해싱 알고리즘 추상화, 향후 알고리즘 마이그레이션 용이
- Cost factor: 12 (권장 범위 10-14, 균형점)

### Alternatives Considered
- **Argon2**: 더 현대적이나 메모리 집약적, 서버 리소스 고려 시 bcrypt가 안전한 선택
- **PBKDF2**: 표준이지만 bcrypt보다 약간 느림

---

## 3. 세션 저장소

### Decision: Redis (세션/Refresh Token 저장)

### Rationale
- Constitution V조 "JWT + Redis 세션 조합 MUST" 준수
- TTL 자동 만료 지원으로 세션 정리 자동화
- 고성능 읽기/쓰기 (로그인/토큰 검증 빈번)
- 클러스터 모드로 고가용성 확보

### Storage Strategy
- **Key 패턴**: `session:{user_id}:{session_id}` → Refresh Token + 메타데이터
- **TTL**: Refresh Token 유효기간(7일)과 동일
- 로그아웃 시 해당 키 삭제로 즉시 무효화

### Alternatives Considered
- **PostgreSQL**: 가능하나 빈번한 조회에 비효율적
- **In-memory (서버)**: 수평 확장 시 세션 불일치 문제

---

## 4. Access Token 무효화 전략

### Decision: Blacklist 방식 (Redis)

### Rationale
- Access Token은 짧은 유효기간(15분)으로 Stateless 유지
- 로그아웃 시 Access Token을 Redis Blacklist에 추가 (남은 TTL만큼)
- 토큰 검증 시 Blacklist 확인 → 있으면 거부

### Key 패턴
- `blacklist:{access_token_jti}` → 만료 시각
- TTL: 토큰 남은 유효기간

### Alternatives Considered
- **Refresh Token만 무효화**: Access Token 15분간 유효 → 보안 위험
- **토큰 버전 증가**: User 테이블 수정 필요, 복잡도 증가

---

## 5. 계정 잠금 메커니즘

### Decision: Redis 카운터 + TTL

### Rationale
- 로그인 실패마다 `login_fail:{email}` 카운터 증가
- 5회 도달 시 `account_lock:{email}` 키 생성 (TTL: 15분)
- 로그인 성공 시 카운터 삭제
- DB 부하 없이 빠른 잠금 판단

### Alternatives Considered
- **User 테이블 failed_attempts 컬럼**: DB 쓰기 부하, 분산 환경 경쟁 조건
- **Rate Limiting (API 레벨)**: IP 기반은 우회 가능, 계정 기반 잠금이 더 효과적

---

## 6. 토큰 구조

### Decision: JWT Claims 구조

### Access Token Claims
```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "exp": 1702200000,
  "iat": 1702199100,
  "jti": "unique_token_id",
  "type": "access"
}
```

### Refresh Token Claims
```json
{
  "sub": "user_uuid",
  "exp": 1702804800,
  "iat": 1702200000,
  "jti": "unique_token_id",
  "session_id": "session_uuid",
  "type": "refresh"
}
```

### Rationale
- `jti` (JWT ID): 토큰 고유 식별자, Blacklist/재사용 방지
- `session_id`: Refresh Token과 Redis 세션 연결
- `type`: Access/Refresh 구분으로 잘못된 사용 방지

---

## 7. API 버전 관리

### Decision: URL Path 버전 (`/v1/auth/*`)

### Rationale
- Constitution I조 "API 버전 관리는 URL 경로로 명시 MUST" 준수
- 명확한 버전 분리, 클라이언트 마이그레이션 용이

### Endpoints
- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `POST /v1/auth/logout`
- `POST /v1/auth/refresh`

---

## 8. 에러 응답 표준

### Decision: RFC 7807 Problem Details

### Rationale
- 표준화된 에러 응답 형식
- 디버깅에 유용한 정보 제공
- 클라이언트 에러 처리 일관성

### Format
```json
{
  "type": "https://api.naecipe.com/errors/auth/invalid-credentials",
  "title": "Authentication Failed",
  "status": 401,
  "detail": "이메일 또는 비밀번호가 올바르지 않습니다.",
  "instance": "/v1/auth/login"
}
```

---

## 9. 의존성 목록

### Production Dependencies
- `fastapi>=0.100.0`
- `python-jose[cryptography]>=3.3.0`
- `passlib[bcrypt]>=1.7.4`
- `pydantic>=2.0.0`
- `sqlalchemy>=2.0.0`
- `asyncpg>=0.28.0` (PostgreSQL async driver)
- `redis>=5.0.0`

### Development Dependencies
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`
- `httpx>=0.24.0` (테스트용 async HTTP client)
- `fakeredis>=2.20.0` (Redis 모킹)

---

## 10. Constitution 준수 확인

| 원칙 | 적용 방안 | 상태 |
|------|----------|------|
| I. API-First | OpenAPI 3.0 스펙 작성 (contracts/) | ✅ |
| II. Microservice | user-service 독립 서비스, User DB 분리 | ✅ |
| III. TDD | Contract 테스트, Integration 테스트 계획 | ✅ |
| IV. Event-Driven | 이벤트 발행 없음 (인증은 내부 서비스) | N/A |
| V. Security | bcrypt 해싱, JWT+Redis, Pydantic 검증 | ✅ |
| VI. Observability | 구조화 로깅, Health Check 계획 | ✅ |
| VII. Simplicity | 최소 기능만 구현, 불필요한 추상화 없음 | ✅ |
