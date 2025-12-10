"""
커서 인코딩/디코딩 유틸리티

커서 기반 페이지네이션을 위한 base64 JSON 커서 처리
"""

import base64
import json
from datetime import datetime
from typing import Any


class CursorError(Exception):
    """커서 관련 예외"""

    pass


def encode_cursor(sort: str, value: Any, recipe_id: str) -> str:
    """
    커서 인코딩

    Args:
        sort: 정렬 기준 (relevance, latest, cook_time, popularity)
        value: 정렬 필드 값
        recipe_id: 레시피 ID (tie-breaker)

    Returns:
        base64 인코딩된 커서 문자열
    """
    if isinstance(value, datetime):
        value = value.isoformat()
    data = {"s": sort, "v": value, "i": recipe_id}
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, Any, str]:
    """
    커서 디코딩

    Args:
        cursor: base64 인코딩된 커서 문자열

    Returns:
        tuple (sort, value, recipe_id)

    Raises:
        CursorError: 잘못된 커서 형식
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)
        return data["s"], data["v"], data["i"]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise CursorError(f"잘못된 커서 형식: {e}") from e
