"""Create users table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table"""
    # Create enum type first using raw SQL to avoid double creation
    # IMPORTANT: Use uppercase values to match Python Enum values (UserStatus.ACTIVE = "ACTIVE")
    op.execute("CREATE TYPE user_status AS ENUM ('ACTIVE', 'INACTIVE', 'LOCKED')")

    # Use postgresql.ENUM with create_type=False since we created it above
    user_status_enum = postgresql.ENUM("ACTIVE", "INACTIVE", "LOCKED", name="user_status", create_type=False)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", user_status_enum, nullable=False, server_default="ACTIVE"),
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
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique index on email
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Create index on status for filtering
    op.create_index("ix_users_status", "users", ["status"], unique=False)


def downgrade() -> None:
    """Drop users table"""
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    # Drop enum type using raw SQL
    op.execute("DROP TYPE user_status")
