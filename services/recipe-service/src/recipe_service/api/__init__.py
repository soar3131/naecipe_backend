"""
API 라우터 모듈

모든 라우터를 export합니다.
"""

from recipe_service.api.recipes import router as recipes_router

__all__ = [
    "recipes_router",
]
