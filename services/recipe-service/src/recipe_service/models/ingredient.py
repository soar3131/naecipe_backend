"""
재료(Ingredient) 모델

레시피의 재료 정보를 관리합니다.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recipe_service.models.base import Base

if TYPE_CHECKING:
    from recipe_service.models.recipe import Recipe


class RecipeIngredient(Base):
    """
    레시피 재료 모델

    레시피에 포함된 재료 정보
    """

    __tablename__ = "recipe_ingredients"

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

    # 재료 정보
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="재료명",
    )
    amount: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="양 (예: 300, 1/2, 약간)",
    )
    unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="단위 (예: g, ml, 개, 큰술)",
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="부가 설명 (예: 다진 것, 잘게 썬 것)",
    )

    # 순서
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="표시 순서",
    )

    # 관계
    recipe: Mapped["Recipe"] = relationship(
        "Recipe",
        back_populates="ingredients",
    )

    @property
    def display_amount(self) -> str:
        """표시용 양"""
        if self.amount and self.unit:
            return f"{self.amount}{self.unit}"
        elif self.amount:
            return self.amount
        elif self.unit:
            return self.unit
        return ""
