# Data Model: OAuth 소셜 로그인

**Feature**: 002-oauth-social-login
**Date**: 2025-12-10

## Entities

### OAuthAccount

소셜 로그인 제공자 계정 정보를 저장하는 엔티티

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | 고유 식별자 |
| user_id | UUID | FK(users.id), NOT NULL | 연결된 사용자 |
| provider | VARCHAR(20) | NOT NULL, INDEX | 제공자 (kakao, google, naver) |
| provider_user_id | VARCHAR(255) | NOT NULL | 제공자의 사용자 ID |
| provider_email | VARCHAR(255) | NULL | 소셜 계정 이메일 |
| created_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW() | 연동 일시 |
| updated_at | TIMESTAMP WITH TZ | NOT NULL, DEFAULT NOW() | 수정 일시 |

**Indexes**:
- `ix_oauth_accounts_user_id` (user_id)
- `ix_oauth_accounts_provider_user` (provider, provider_user_id) UNIQUE

**Constraints**:
- 동일 user_id에 동일 provider는 하나만 허용
- provider는 ENUM('kakao', 'google', 'naver')으로 제한

### User (기존, 확장 없음)

SPEC-001에서 정의된 User 엔티티를 그대로 사용. 소셜 로그인으로 생성된 사용자는:
- `password_hash`: NULL 허용 필요 (소셜 전용 사용자)
- `status`: ACTIVE로 생성

**참고**: password_hash NULL 허용을 위한 마이그레이션 필요

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                │
│  (SPEC-001에서 정의)                                         │
├─────────────────────────────────────────────────────────────┤
│  id: UUID (PK)                                              │
│  email: VARCHAR(255) UNIQUE                                 │
│  password_hash: VARCHAR(255) NULLABLE ← 수정 필요           │
│  status: ENUM('ACTIVE', 'INACTIVE', 'LOCKED')               │
│  created_at: TIMESTAMP                                      │
│  updated_at: TIMESTAMP                                      │
│  locked_until: TIMESTAMP NULLABLE                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     OAuthAccount                            │
│  (신규)                                                      │
├─────────────────────────────────────────────────────────────┤
│  id: UUID (PK)                                              │
│  user_id: UUID (FK → users.id)                              │
│  provider: VARCHAR(20)                                      │
│  provider_user_id: VARCHAR(255)                             │
│  provider_email: VARCHAR(255) NULLABLE                      │
│  created_at: TIMESTAMP                                      │
│  updated_at: TIMESTAMP                                      │
├─────────────────────────────────────────────────────────────┤
│  UNIQUE: (provider, provider_user_id)                       │
│  UNIQUE: (user_id, provider)                                │
└─────────────────────────────────────────────────────────────┘
```

## State Transitions

### OAuthAccount 생성 플로우

```
[OAuth 인증 완료]
       │
       ▼
[provider_user_id로 OAuthAccount 조회]
       │
       ├── 있음 → [해당 user_id로 로그인]
       │
       └── 없음 → [email로 User 조회]
                        │
                        ├── 있음 → [OAuthAccount 생성, 기존 User에 연동]
                        │
                        └── 없음 → [User 생성] → [OAuthAccount 생성]
```

## Validation Rules

### Provider

```python
class OAuthProvider(str, Enum):
    KAKAO = "kakao"
    GOOGLE = "google"
    NAVER = "naver"
```

### Provider User ID

- 최대 255자
- 빈 문자열 불가
- 제공자마다 형식 다름 (숫자, 문자열 혼합 가능)

### Provider Email

- 유효한 이메일 형식
- NULL 허용 (권한 거부 시)
- 실제로는 이메일 필수로 구현 (이메일 없으면 에러)

## Migration Notes

### 002_create_oauth_accounts.py

```python
def upgrade():
    # 1. users.password_hash NULL 허용으로 변경
    op.alter_column('users', 'password_hash', nullable=True)

    # 2. oauth_provider ENUM 생성
    op.execute("CREATE TYPE oauth_provider AS ENUM ('kakao', 'google', 'naver')")

    # 3. oauth_accounts 테이블 생성
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.Enum('kakao', 'google', 'naver', name='oauth_provider'), nullable=False),
        sa.Column('provider_user_id', sa.String(255), nullable=False),
        sa.Column('provider_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # 4. 인덱스 생성
    op.create_index('ix_oauth_accounts_user_id', 'oauth_accounts', ['user_id'])
    op.create_index('ix_oauth_accounts_provider_user', 'oauth_accounts', ['provider', 'provider_user_id'], unique=True)
    op.create_index('ix_oauth_accounts_user_provider', 'oauth_accounts', ['user_id', 'provider'], unique=True)

def downgrade():
    op.drop_table('oauth_accounts')
    op.execute("DROP TYPE oauth_provider")
    op.alter_column('users', 'password_hash', nullable=False)
```

## SQLAlchemy Model

```python
class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[OAuthProvider] = mapped_column(Enum(OAuthProvider, name="oauth_provider"), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider_user"),
        UniqueConstraint("user_id", "provider", name="uq_oauth_accounts_user_provider"),
    )
```
