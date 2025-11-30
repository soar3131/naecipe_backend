"""Cookbook Service FastAPI Application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cookbook_service.api.health import router as health_router
from cookbook_service.core.config import settings

app = FastAPI(
    title="Cookbook Service",
    description="레시피북 및 피드백 서비스",
    version="0.1.0",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health_router, tags=["health"])


@app.get("/")
async def root():
    return {
        "service": "cookbook-service",
        "version": "0.1.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cookbook_service.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
    )
