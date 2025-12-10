"""
조리 단계(Cooking Step) 모델

레시피의 조리 단계 정보를 관리합니다.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipe_service.models.base import Base

if TYPE_CHECKING:
    from recipe_service.models.recipe import Recipe


class CookingStep(Base):
    """
    조리 단계 모델

    레시피의 순차적인 조리 과정
    """

    __tablename__ = "cooking_steps"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    recipe_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 단계 정보
    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="단계 번호 (1부터 시작)",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="단계 설명",
    )
    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="단계별 이미지 URL",
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="단계 소요 시간 (초)",
    )
    tip: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="조리 팁",
    )

    # 관계
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="steps",
    )

    @property
    def duration_minutes(self) -> int | None:
        """소요 시간 (분)"""
        if self.duration_seconds is None:
            return None
        return self.duration_seconds // 60
