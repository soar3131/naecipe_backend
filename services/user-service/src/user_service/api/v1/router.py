"""API v1 router aggregator"""

from fastapi import APIRouter

from user_service.api.v1.auth import router as auth_router
from user_service.api.v1.oauth import router as oauth_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(oauth_router, prefix="/auth/oauth", tags=["oauth"])
