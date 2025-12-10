"""Health check endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.db.redis import get_redis_client
from user_service.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """기본 헬스 체크 - 서비스 생존 확인"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
):
    """준비 상태 체크 - 의존성 연결 확인"""
    checks = {
        "database": False,
        "redis": False,
    }

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    # Redis check
    try:
        redis = await get_redis_client()
        await redis.ping()
        checks["redis"] = True
    except Exception:
        pass

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks,
    }
