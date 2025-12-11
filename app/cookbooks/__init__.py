"""
Cookbooks 모듈

레시피북 CRUD 기능을 담당합니다.
저장된 레시피, 피드백 기능은 추후 구현 예정 (SPEC-008)
"""

from app.cookbooks.exceptions import (
    CannotDeleteDefaultCookbookError,
    CookbookNotFoundError,
)
from app.cookbooks.models import Cookbook
from app.cookbooks.router import router
from app.cookbooks.schemas import (
    CookbookCreateRequest,
    CookbookListResponse,
    CookbookReorderRequest,
    CookbookResponse,
    CookbookUpdateRequest,
)
from app.cookbooks.services import CookbookService

__all__ = [
    # Router
    "router",
    # Models
    "Cookbook",
    # Schemas
    "CookbookCreateRequest",
    "CookbookUpdateRequest",
    "CookbookReorderRequest",
    "CookbookResponse",
    "CookbookListResponse",
    # Services
    "CookbookService",
    # Exceptions
    "CookbookNotFoundError",
    "CannotDeleteDefaultCookbookError",
]
