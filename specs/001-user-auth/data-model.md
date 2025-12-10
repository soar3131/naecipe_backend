# Data Model: 사용자 인증 기본

**Feature Branch**: `001-user-auth`
**Date**: 2025-12-10

## 엔티티 다이어그램

```
┌─────────────────────────────────────────┐
│                 User                     │
├─────────────────────────────────────────┤
│ id: UUID (PK)                           │
│ email: VARCHAR(255) UNIQUE NOT NULL     │
│ password_hash: VARCHAR(255) NOT NULL    │
│ status: ENUM('active','inactive','locked')│
│ created_at: TIMESTAMP                   │
│ updated_at: TIMESTAMP                   │
│ locked_until: TIMESTAMP NULL            │
└─────────────────────────────────────────┘
          │
          │ 1:N
          ▼
┌─────────────────────────────────────────┐
│                Session                   │
│            (Redis 저장)                  │
├─────────────────────────────────────────┤
│ session_id: UUID (KEY)                  │
│ user_id: UUID (FK → User)               │
│ refresh_token_jti: VARCHAR(255)         │
│ device_info: JSON                       │
│ created_at: TIMESTAMP                   │
│ expires_at: TIMESTAMP                   │
└─────────────────────────────────────────┘
```

---

## 1. User (PostgreSQL)

사용자 계정 정보를 저장합니다.

### 필드 정의

| 필드 | 타입 | 제약 조건 | 설명 |
|------|------|----------|------|
| `id` | UUID | PK, DEFAULT uuid_generate_v4() | 사용자 고유 식별자 |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | 로그인용 이메일 (소문자 저장) |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt 해싱된 비밀번호 |
| `status` | ENUM | NOT NULL, DEFAULT 'active' | 계정 상태 |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | 계정 생성 시각 |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | 마지막 수정 시각 |
| `locked_until` | TIMESTAMP | NULL | 잠금 해제 시각 (NULL = 미잠금) |

### 상태 (Status) ENUM

```sql
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'locked');
```

| 값 | 설명 |
|----|------|
| `active` | 정상 활성 계정 |
| `inactive` | 비활성화된 계정 (관리자 조치) |
| `locked` | 로그인 실패로 일시 잠금 |

### 인덱스

```sql
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
```

### 검증 규칙

- **email**: RFC 5322 이메일 형식, 최대 255자, 소문자로 정규화
- **password_hash**: bcrypt 해시 (60자 고정)

---

## 2. Session (Redis)

사용자 로그인 세션을 Redis에 저장합니다.

### Key 패턴

```
session:{user_id}:{session_id}
```

### Value 구조 (JSON)

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "refresh_token_jti": "unique-jti-string",
  "device_info": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1"
  },
  "created_at": "2025-12-10T09:00:00Z",
  "expires_at": "2025-12-17T09:00:00Z"
}
```

### TTL

- Refresh Token 유효기간과 동일: **7일 (604800초)**

### 관련 Redis Keys

| Key 패턴 | 용도 | TTL |
|---------|------|-----|
| `session:{user_id}:{session_id}` | 세션 정보 | 7일 |
| `blacklist:{access_token_jti}` | 로그아웃된 Access Token | 15분 (남은 유효기간) |
| `login_fail:{email}` | 로그인 실패 카운터 | 15분 |

---

## 3. 상태 전이 다이어그램

### User Status

```
                    ┌─────────────────┐
                    │    inactive     │
                    └────────┬────────┘
                             │ (관리자 활성화)
                             ▼
┌─────────┐  (5회 실패)  ┌─────────┐
│  locked │◀─────────────│  active │
└────┬────┘              └────┬────┘
     │ (15분 경과)            │
     └────────────────────────┘
```

### Session Lifecycle

```
[로그인 요청]
     │
     ▼
┌─────────────────┐
│  세션 생성      │ → Redis에 저장
│  토큰 발급      │ → Access + Refresh
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Active Session │ ◀───────────┐
└────────┬────────┘             │
         │                      │
    ┌────┴────┐                 │
    │         │                 │
    ▼         ▼                 │
[로그아웃] [토큰 갱신] ──────────┘
    │
    ▼
┌─────────────────┐
│  세션 삭제      │ → Redis에서 제거
│  토큰 Blacklist │ → Access Token
└─────────────────┘
```

---

## 4. 마이그레이션 SQL

```sql
-- 001_create_users_table.sql

-- UUID 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 사용자 상태 ENUM
CREATE TYPE user_status AS ENUM ('active', 'inactive', 'locked');

-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    locked_until TIMESTAMP WITH TIME ZONE NULL,

    CONSTRAINT uk_users_email UNIQUE (email),
    CONSTRAINT chk_users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 인덱스
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 5. Pydantic 스키마 (참고용)

```python
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserInDB(UserBase):
    id: UUID
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    locked_until: datetime | None = None

class SessionData(BaseModel):
    user_id: UUID
    refresh_token_jti: str
    device_info: dict
    created_at: datetime
    expires_at: datetime
```

---

## 6. 관계 요약

| 관계 | 설명 |
|------|------|
| User → Session | 1:N (한 사용자가 여러 기기에서 로그인 가능) |
| Session → Refresh Token | 1:1 (세션당 하나의 Refresh Token) |

---

## 7. SPEC-002, SPEC-003과의 경계

### 이 스펙에서 정의하지 않는 것

- **OAuth Accounts 테이블**: SPEC-002에서 `oauth_accounts` 테이블 정의
- **User Profile 테이블**: SPEC-003에서 `user_profiles`, `taste_preferences` 테이블 정의

### 확장 포인트

- `users.id`가 다른 테이블의 Foreign Key로 사용될 예정
- SPEC-002, SPEC-003에서 추가 필드나 관계가 정의될 수 있음
