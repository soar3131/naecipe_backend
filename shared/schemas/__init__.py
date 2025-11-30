"""
공통 Pydantic 스키마 패키지

서비스 간 공유되는 Pydantic 모델을 정의합니다.
"""

from shared.schemas.base import (
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
)
from shared.schemas.health import (
    DependencyChecks,
    HealthResponse,
    ReadinessResponse,
)

__all__ = [
    "BaseResponse",
    "ErrorResponse",
    "ErrorDetail",
    "PaginatedResponse",
    "HealthResponse",
    "ReadinessResponse",
    "DependencyChecks",
]
