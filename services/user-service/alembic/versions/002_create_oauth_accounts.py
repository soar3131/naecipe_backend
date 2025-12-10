"""Create oauth_accounts table and update users.password_hash nullable

Revision ID: 002
Revises: 001
Create Date: 2025-12-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create oauth_accounts table and update users.password_hash to nullable"""
    # 1. users.password_hash를 nullable로 변경 (소셜 로그인 전용 사용자용)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)

    # 2. oauth_provider ENUM 생성
    op.execute("CREATE TYPE oauth_provider AS ENUM ('kakao', 'google', 'naver')")

    # 3. oauth_accounts 테이블 생성
    oauth_provider_enum = postgresql.ENUM(
        "kakao", "google", "naver", name="oauth_provider", create_type=False
    )

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", oauth_provider_enum, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 4. 인덱스 생성
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
    op.create_index(
        "ix_oauth_accounts_provider_user",
        "oauth_accounts",
        ["provider", "provider_user_id"],
        unique=True,
    )
    op.create_index(
        "ix_oauth_accounts_user_provider",
        "oauth_accounts",
        ["user_id", "provider"],
        unique=True,
    )


def downgrade() -> None:
    """Drop oauth_accounts table and revert users.password_hash to not nullable"""
    # 인덱스 삭제
    op.drop_index("ix_oauth_accounts_user_provider", table_name="oauth_accounts")
    op.drop_index("ix_oauth_accounts_provider_user", table_name="oauth_accounts")
    op.drop_index("ix_oauth_accounts_user_id", table_name="oauth_accounts")

    # oauth_accounts 테이블 삭제
    op.drop_table("oauth_accounts")

    # ENUM 타입 삭제
    op.execute("DROP TYPE oauth_provider")

    # users.password_hash를 NOT NULL로 복원
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
