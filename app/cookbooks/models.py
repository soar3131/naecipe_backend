"""
Cookbooks 모듈 모델

레시피북 엔티티를 정의합니다.
"""

from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base, TimestampMixin


class Cookbook(Base, TimestampMixin):
    """
    레시피북 모델

    사용자가 레시피를 분류하고 저장하는 컨테이너
    """

    __tablename__ = "cookbooks"

    # Partial Unique Index는 Alembic 마이그레이션에서 직접 SQL로 생성
    # CREATE UNIQUE INDEX uq_cookbooks_user_default ON cookbooks (user_id) WHERE is_default = TRUE;

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="소유 사용자 ID",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="레시피북 이름",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="레시피북 설명",
    )
    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="커버 이미지 URL",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="정렬 순서 (오름차순)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="기본 레시피북 여부",
    )

    # 관계 (User는 users 모듈에서 정의)
    # saved_recipes 관계는 SPEC-008에서 추가 예정


# Partial Unique Index를 위한 DDL (Alembic 마이그레이션에서 사용)
# CREATE UNIQUE INDEX uq_cookbooks_user_default
# ON cookbooks (user_id)
# WHERE is_default = TRUE;
