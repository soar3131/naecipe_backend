"""User Service FastAPI Application"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from user_service.api.health import router as health_router
from user_service.api.v1.router import api_router
from user_service.core.config import settings
from user_service.core.exceptions import (
    ProblemDetail,
    http_exception_handler,
    problem_detail_exception_handler,
)
from user_service.db.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler"""
    # Startup
    yield
    # Shutdown
    await close_redis()


app = FastAPI(
    title="User Service",
    description="사용자 인증 및 관리 서비스",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(ProblemDetail, problem_detail_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Routers
app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix="/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "user_service.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
