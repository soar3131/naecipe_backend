"""
Recipe Service 메인 애플리케이션

FastAPI 앱 인스턴스와 라우터를 정의합니다.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from recipe_service.api.health import router as health_router
from recipe_service.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 수명 주기 관리"""
    # 시작 시 실행
    yield
    # 종료 시 실행


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="내시피(Naecipe) 레시피 서비스 - 레시피 CRUD 및 검색",
    version="1.0.0",
    lifespan=lifespan,
)

# 라우터 등록
app.include_router(health_router, tags=["Health"])


@app.get("/")
async def root() -> dict[str, str]:
    """루트 엔드포인트"""
    return {"service": settings.SERVICE_NAME, "status": "running"}
