"""
에러 핸들링 미들웨어

커스텀 예외와 전역 예외 핸들러를 정의합니다.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from recipe_service.schemas.common import ErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


# 커스텀 예외 클래스
class ServiceError(Exception):
    """서비스 기본 예외"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: list[ErrorDetail] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


class RecipeNotFoundError(ServiceError):
    """레시피를 찾을 수 없음"""

    def __init__(self, recipe_id: str):
        super().__init__(
            code="RECIPE_NOT_FOUND",
            message=f"레시피를 찾을 수 없습니다: {recipe_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ChefNotFoundError(ServiceError):
    """요리사를 찾을 수 없음"""

    def __init__(self, chef_id: str):
        super().__init__(
            code="CHEF_NOT_FOUND",
            message=f"요리사를 찾을 수 없습니다: {chef_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidCursorError(ServiceError):
    """잘못된 커서 값"""

    def __init__(self, cursor: str):
        super().__init__(
            code="INVALID_CURSOR",
            message=f"잘못된 페이지네이션 커서입니다: {cursor}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


def create_error_response(
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    """에러 응답 딕셔너리 생성"""
    return ErrorResponse(
        code=code,
        message=message,
        details=details or [],
    ).model_dump()


async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """ServiceError 예외 핸들러"""
    logger.warning(
        f"Service error: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "path": str(request.url),
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.code, exc.message, exc.details),
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Pydantic ValidationError 예외 핸들러"""
    details = [
        ErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
        )
        for error in exc.errors()
    ]
    logger.warning(
        f"Validation error: {len(details)} errors",
        extra={
            "path": str(request.url),
            "method": request.method,
            "errors": [d.model_dump() for d in details],
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            "VALIDATION_ERROR",
            "요청 데이터 검증에 실패했습니다",
            details,
        ),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 핸들러"""
    logger.exception(
        f"Unhandled exception: {exc}",
        extra={
            "path": str(request.url),
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            "INTERNAL_SERVER_ERROR",
            "서버 내부 오류가 발생했습니다",
        ),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """FastAPI 앱에 예외 핸들러 등록"""
    app.add_exception_handler(ServiceError, service_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
