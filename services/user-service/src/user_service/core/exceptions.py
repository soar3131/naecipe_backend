"""Custom exceptions with RFC 7807 ProblemDetail format"""

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class ProblemDetail(Exception):
    """RFC 7807 Problem Details exception"""

    def __init__(
        self,
        type_uri: str,
        title: str,
        status: int,
        detail: str,
        instance: str | None = None,
        extensions: dict[str, Any] | None = None,
    ):
        self.type = type_uri
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance
        self.extensions = extensions or {}
        super().__init__(detail)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.instance:
            result["instance"] = self.instance
        result.update(self.extensions)
        return result


# Base error types
ERROR_BASE_URI = "https://api.naecipe.com/errors"


class ValidationError(ProblemDetail):
    """Validation error (400)"""

    def __init__(self, detail: str, instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/validation",
            title="Validation Error",
            status=400,
            detail=detail,
            instance=instance,
        )


class AuthenticationError(ProblemDetail):
    """Authentication error (401)"""

    def __init__(
        self,
        detail: str,
        instance: str | None = None,
        error_code: str = "invalid-credentials",
    ):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/auth/{error_code}",
            title="Authentication Failed",
            status=401,
            detail=detail,
            instance=instance,
        )


class TokenRevokedError(ProblemDetail):
    """Token revoked error (401)"""

    def __init__(self, instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/auth/token-revoked",
            title="Token Revoked",
            status=401,
            detail="토큰이 무효화되었습니다. 다시 로그인해주세요.",
            instance=instance,
        )


class InvalidTokenError(ProblemDetail):
    """Invalid token error (401)"""

    def __init__(self, detail: str = "유효하지 않은 토큰입니다.", instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/auth/invalid-token",
            title="Invalid Token",
            status=401,
            detail=detail,
            instance=instance,
        )


class EmailExistsError(ProblemDetail):
    """Email already exists error (409)"""

    def __init__(self, instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/auth/email-exists",
            title="Email Already Exists",
            status=409,
            detail="이미 등록된 이메일 주소입니다.",
            instance=instance,
        )


class AccountLockedError(ProblemDetail):
    """Account locked error (423)"""

    def __init__(self, minutes_remaining: int = 15, instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/auth/account-locked",
            title="Account Locked",
            status=423,
            detail=f"연속된 로그인 실패로 계정이 잠겼습니다. {minutes_remaining}분 후 다시 시도해주세요.",
            instance=instance,
            extensions={"retry_after_minutes": minutes_remaining},
        )


class UserNotFoundError(ProblemDetail):
    """User not found error (404)"""

    def __init__(self, instance: str | None = None):
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/user/not-found",
            title="User Not Found",
            status=404,
            detail="사용자를 찾을 수 없습니다.",
            instance=instance,
        )


async def problem_detail_exception_handler(
    request: Request, exc: ProblemDetail
) -> JSONResponse:
    """Exception handler for ProblemDetail exceptions"""
    response_data = exc.to_dict()
    if exc.instance is None:
        response_data["instance"] = str(request.url.path)
    return JSONResponse(
        status_code=exc.status,
        content=response_data,
        media_type="application/problem+json",
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Convert HTTPException to RFC 7807 format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"{ERROR_BASE_URI}/http/{exc.status_code}",
            "title": "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path),
        },
        media_type="application/problem+json",
    )
