"""Health check endpoints"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """기본 헬스 체크"""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """준비 상태 체크"""
    return {"status": "ready"}
