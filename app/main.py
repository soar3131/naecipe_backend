"""
내시피(Naecipe) 백엔드 메인 애플리케이션

모듈러 모놀리스 아키텍처 v2.0
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import __version__
from app.core import (
    DependencyChecks,
    HealthResponse,
    ReadinessResponse,
    get_logger,
    settings,
    setup_logging,
)
from app.core.exceptions import register_exception_handlers
from app.infra.database import engine
from app.infra.redis import get_redis_client

# 로깅 설정
setup_logging(
    service_name="naecipe",
    log_level=settings.LOG_LEVEL,
    json_format=settings.ENVIRONMENT == "production",
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """앱 라이프사이클 관리"""
    logger.info(
        "Starting Naecipe Backend",
        version=__version__,
        environment=settings.ENVIRONMENT,
    )

    yield

    # 종료 시 정리
    logger.info("Shutting down Naecipe Backend")
    await engine.dispose()


def create_app() -> FastAPI:
    """FastAPI 앱 생성"""
    app = FastAPI(
        title="내시피(Naecipe) API",
        description="AI 기반 맞춤형 레시피 보정 서비스",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 예외 핸들러 등록
    register_exception_handlers(app)

    # 라우터 등록
    _include_routers(app)

    # 헬스체크 엔드포인트
    _add_health_endpoints(app)

    return app


def _include_routers(app: FastAPI) -> None:
    """라우터 등록"""
    from app.cookbooks import router as cookbooks_router
    from app.recipes import router as recipes_router
    from app.users import router as users_router

    # Users 모듈 (인증, 프로필, 취향 설정, OAuth)
    app.include_router(
        users_router,
        prefix="/api/v1",
        tags=["users"],
    )

    # Recipes 모듈 (레시피, 요리사, 검색)
    app.include_router(
        recipes_router,
        prefix="/api/v1",
        tags=["recipes"],
    )

    # Cookbooks 모듈 (레시피북 CRUD)
    app.include_router(
        cookbooks_router,
        prefix="/api/v1",
        tags=["cookbooks"],
    )

    # 추후 구현 예정 모듈들은 여기에 추가
    # app.include_router(ai_agent_router, prefix="/api/v1")
    # app.include_router(notifications_router, prefix="/api/v1")


def _add_health_endpoints(app: FastAPI) -> None:
    """헬스체크 엔드포인트 추가"""

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Liveness 체크",
    )
    async def health() -> HealthResponse:
        """애플리케이션 상태 확인"""
        return HealthResponse(
            service="naecipe-backend",
            version=__version__,
        )

    @app.get(
        "/ready",
        response_model=ReadinessResponse,
        tags=["health"],
        summary="Readiness 체크",
    )
    async def ready() -> ReadinessResponse:
        """의존 서비스 연결 상태 확인"""
        checks = DependencyChecks()

        # Database 연결 확인
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks.database = True
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            checks.database = False

        # Redis 연결 확인
        try:
            redis = await get_redis_client()
            await redis.ping()
            checks.redis = True
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            checks.redis = False

        # 전체 상태 결정
        is_ready = checks.database  # Redis는 선택적
        status = "ready" if is_ready else "not_ready"

        return ReadinessResponse(
            status=status,
            service="naecipe-backend",
            checks=checks,
        )


# 앱 인스턴스 생성
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
