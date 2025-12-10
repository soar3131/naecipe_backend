# User Service

사용자 인증 및 관리 마이크로서비스

## 개요

이 서비스는 내시피(Naecipe) 백엔드의 사용자 인증을 담당합니다.

### 주요 기능

- 이메일 기반 회원가입
- JWT 토큰 기반 로그인/로그아웃
- Access Token / Refresh Token 관리
- 계정 잠금 (5회 로그인 실패 시)

## 기술 스택

- **Framework**: FastAPI 0.100+
- **Database**: PostgreSQL 15+ (async SQLAlchemy 2.0)
- **Cache**: Redis 7+
- **Auth**: python-jose (JWT), passlib (bcrypt)
- **Migration**: Alembic

## 프로젝트 구조

```
services/user-service/
├── alembic/                  # 데이터베이스 마이그레이션
│   ├── versions/
│   │   └── 001_create_users.py
│   └── env.py
├── src/user_service/
│   ├── api/
│   │   ├── deps.py           # API 의존성 (인증 등)
│   │   ├── health.py         # 헬스 체크 엔드포인트
│   │   └── v1/
│   │       ├── auth.py       # 인증 엔드포인트
│   │       └── router.py     # API 라우터
│   ├── core/
│   │   ├── config.py         # 설정
│   │   ├── exceptions.py     # 커스텀 예외 (RFC 7807)
│   │   ├── logging.py        # 구조화 로깅
│   │   └── security.py       # 비밀번호/JWT 유틸리티
│   ├── db/
│   │   ├── base.py           # SQLAlchemy Base
│   │   ├── redis.py          # Redis 클라이언트
│   │   └── session.py        # 데이터베이스 세션
│   ├── models/
│   │   └── user.py           # User 모델
│   ├── schemas/
│   │   ├── auth.py           # 인증 스키마
│   │   └── user.py           # 사용자 스키마
│   ├── services/
│   │   ├── auth.py           # 인증 서비스
│   │   ├── session.py        # 세션 서비스 (Redis)
│   │   └── user.py           # 사용자 서비스
│   └── main.py               # FastAPI 앱
├── tests/
│   ├── contract/             # 계약 테스트
│   ├── integration/          # 통합 테스트
│   └── unit/                 # 단위 테스트
├── Dockerfile
└── pyproject.toml
```

## API 엔드포인트

### 인증 API (v1)

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/v1/auth/register` | 회원가입 |
| POST | `/v1/auth/login` | 로그인 |
| GET | `/v1/auth/me` | 현재 사용자 조회 |
| POST | `/v1/auth/refresh` | 토큰 갱신 |
| POST | `/v1/auth/logout` | 로그아웃 |

### 헬스 체크

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 서비스 생존 확인 |
| GET | `/ready` | 서비스 준비 상태 (DB, Redis 연결 확인) |

## 로컬 개발 환경 설정

### 사전 요구사항

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- uv (패키지 관리자)

### 설치

```bash
# 프로젝트 디렉토리로 이동
cd services/user-service

# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 설정

# 데이터베이스 마이그레이션
uv run alembic upgrade head

# 개발 서버 실행
uv run uvicorn user_service.main:app --reload --port 8002
```

### 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 연결 URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | JWT 서명 비밀키 | (필수) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 유효기간 (분) | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 유효기간 (일) | `7` |
| `DEBUG` | 디버그 모드 | `false` |

## 테스트

```bash
# 전체 테스트 실행
uv run pytest

# 단위 테스트만
uv run pytest tests/unit/

# 계약 테스트만
uv run pytest tests/contract/

# 통합 테스트만
uv run pytest tests/integration/

# 커버리지 포함
uv run pytest --cov=user_service
```

## Docker

```bash
# 이미지 빌드
docker build -t naecipe/user-service .

# 컨테이너 실행
docker run -p 8002:8002 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  -e JWT_SECRET_KEY=... \
  naecipe/user-service
```

## API 문서

개발 서버 실행 후:

- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc
- OpenAPI JSON: http://localhost:8002/openapi.json

## 보안 고려사항

- 비밀번호는 bcrypt로 해시화
- JWT는 HS256 알고리즘 사용
- Access Token: 15분 유효
- Refresh Token: 7일 유효, Redis에 저장
- 5회 로그인 실패 시 15분간 계정 잠금
- 로그아웃 시 Access Token 블랙리스트 추가
