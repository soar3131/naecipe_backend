"""
Recipe Service 메인 애플리케이션

FastAPI 앱 인스턴스와 라우터를 정의합니다.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from recipe_service.api.chefs import router as chefs_router
from recipe_service.api.health import router as health_router
from recipe_service.api.recipes import router as recipes_router
from recipe_service.core.config import settings
from recipe_service.database import close_db
from recipe_service.logging_config import setup_logging
from recipe_service.middleware.error_handler import setup_exception_handlers


# 로깅 초기화
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """애플리케이션 수명 주기 관리"""
    # 시작 시 실행
    from recipe_service.cache import get_redis_cache
    from recipe_service.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Recipe Service 시작", port=settings.SERVICE_PORT)

    yield

    # 종료 시 실행
    logger.info("Recipe Service 종료 중...")
    cache = await get_redis_cache()
    await cache.close()
    await close_db()
    logger.info("Recipe Service 종료 완료")


app = FastAPI(
    title=settings.SERVICE_NAME,
    description="내시피(Naecipe) 레시피 서비스 - 원본 레시피 조회 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 예외 핸들러 등록
setup_exception_handlers(app)

# 라우터 등록
app.include_router(health_router, tags=["Health"])
app.include_router(recipes_router, tags=["Recipes"])
app.include_router(chefs_router, tags=["Chefs"])


@app.get("/")
async def root() -> dict[str, str]:
    """루트 엔드포인트"""
    return {"service": settings.SERVICE_NAME, "status": "running"}
