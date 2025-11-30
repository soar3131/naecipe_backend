"""
구조화된 로깅 설정

structlog를 사용한 JSON 로깅을 설정합니다.
민감 정보 마스킹 프로세서를 포함합니다.
"""

import logging
import sys
from typing import Any

import structlog

# 민감 정보 마스킹 대상 키워드
SENSITIVE_KEYWORDS: set[str] = {
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "credential",
    "private_key",
    "access_key",
    "secret_key",
}


def _mask_sensitive_processor(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    structlog 프로세서: 민감 정보 마스킹

    로그 이벤트에서 민감한 키를 자동으로 마스킹합니다.
    """
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in SENSITIVE_KEYWORDS):
            event_dict[key] = "***MASKED***"
        elif isinstance(event_dict[key], dict):
            event_dict[key] = mask_sensitive_data(event_dict[key])
    return event_dict


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    json_format: bool = True,
    mask_sensitive: bool = True,
) -> None:
    """
    구조화된 로깅 설정

    Args:
        service_name: 서비스 이름 (로그에 포함)
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: JSON 포맷 사용 여부 (False면 콘솔 포맷)
        mask_sensitive: 민감 정보 마스킹 여부
    """
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)

    # 공유 프로세서
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # 민감 정보 마스킹 프로세서 추가
    if mask_sensitive:
        shared_processors.append(_mask_sensitive_processor)

    if json_format:
        # 프로덕션: JSON 포맷
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # 개발: 컬러 콘솔 포맷
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 표준 logging 설정 (uvicorn 등)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    로거 인스턴스 반환

    Args:
        name: 로거 이름 (None이면 루트 로거)

    Returns:
        structlog BoundLogger 인스턴스
    """
    return structlog.get_logger(name)


def mask_sensitive_data(data: dict[str, Any], sensitive_keys: set[str] | None = None) -> dict[str, Any]:
    """
    민감한 데이터 마스킹

    Args:
        data: 마스킹할 데이터
        sensitive_keys: 마스킹할 키 목록 (기본: password, secret, token, api_key)

    Returns:
        마스킹된 데이터
    """
    if sensitive_keys is None:
        sensitive_keys = {"password", "secret", "token", "api_key", "authorization"}

    masked = {}
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            masked[key] = value

    return masked
