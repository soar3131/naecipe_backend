"""
Core 모듈

공통 설정, 보안, 의존성, 예외 처리, 로깅을 제공합니다.
"""

from app.core.config import settings
from app.core.exceptions import ProblemDetail
from app.core.logging import get_logger, mask_sensitive_data, setup_logging
from app.core.schemas import (
    BaseResponse,
    DependencyChecks,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    ReadinessResponse,
)

__all__ = [
    # Config
    "settings",
    # Exceptions
    "ProblemDetail",
    # Logging
    "setup_logging",
    "get_logger",
    "mask_sensitive_data",
    # Schemas
    "BaseResponse",
    "ErrorDetail",
    "ErrorResponse",
    "PaginatedResponse",
    "HealthResponse",
    "DependencyChecks",
    "ReadinessResponse",
]
