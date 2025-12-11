"""
커서 기반 페이지네이션 유틸리티

유사도 기반 정렬을 위한 커서 인코딩/디코딩을 제공합니다.
"""

import base64
import json
from dataclasses import dataclass
from typing import Any


class CursorDecodeError(Exception):
    """커서 디코딩 오류"""

    pass


@dataclass
class SimilarityCursor:
    """유사도 기반 페이지네이션 커서"""

    similarity_score: float  # 유사도 점수
    secondary_score: float  # 보조 정렬 점수 (exposure_score, view_count 등)
    recipe_id: str  # 레시피 ID (동점 처리용)


def encode_similarity_cursor(cursor: SimilarityCursor) -> str:
    """
    유사도 커서를 Base64 문자열로 인코딩

    Args:
        cursor: 유사도 커서 데이터

    Returns:
        Base64 인코딩된 커서 문자열
    """
    data = {
        "sim": cursor.similarity_score,
        "sec": cursor.secondary_score,
        "id": cursor.recipe_id,
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_similarity_cursor(cursor: str) -> SimilarityCursor:
    """
    Base64 커서 문자열을 유사도 커서로 디코딩

    Args:
        cursor: Base64 인코딩된 커서 문자열

    Returns:
        유사도 커서 데이터

    Raises:
        CursorDecodeError: 잘못된 커서 형식
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)

        return SimilarityCursor(
            similarity_score=float(data["sim"]),
            secondary_score=float(data["sec"]),
            recipe_id=str(data["id"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise CursorDecodeError(f"잘못된 커서 형식: {e}") from e


@dataclass
class ViewCountCursor:
    """조회수 기반 페이지네이션 커서 (같은 요리사, 카테고리 인기용)"""

    view_count: int  # 조회수
    exposure_score: float  # 노출 점수 (보조 정렬)
    recipe_id: str  # 레시피 ID (동점 처리용)


def encode_view_count_cursor(cursor: ViewCountCursor) -> str:
    """
    조회수 커서를 Base64 문자열로 인코딩

    Args:
        cursor: 조회수 커서 데이터

    Returns:
        Base64 인코딩된 커서 문자열
    """
    data = {
        "vc": cursor.view_count,
        "exp": cursor.exposure_score,
        "id": cursor.recipe_id,
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_view_count_cursor(cursor: str) -> ViewCountCursor:
    """
    Base64 커서 문자열을 조회수 커서로 디코딩

    Args:
        cursor: Base64 인코딩된 커서 문자열

    Returns:
        조회수 커서 데이터

    Raises:
        CursorDecodeError: 잘못된 커서 형식
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)

        return ViewCountCursor(
            view_count=int(data["vc"]),
            exposure_score=float(data["exp"]),
            recipe_id=str(data["id"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise CursorDecodeError(f"잘못된 커서 형식: {e}") from e


@dataclass
class TagCountCursor:
    """태그 수 기반 페이지네이션 커서 (태그 기반 관련 레시피용)"""

    shared_tags_count: int  # 공유 태그 수
    exposure_score: float  # 노출 점수 (보조 정렬)
    recipe_id: str  # 레시피 ID (동점 처리용)


def encode_tag_count_cursor(cursor: TagCountCursor) -> str:
    """
    태그 수 커서를 Base64 문자열로 인코딩

    Args:
        cursor: 태그 수 커서 데이터

    Returns:
        Base64 인코딩된 커서 문자열
    """
    data = {
        "tc": cursor.shared_tags_count,
        "exp": cursor.exposure_score,
        "id": cursor.recipe_id,
    }
    json_str = json.dumps(data, ensure_ascii=False)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_tag_count_cursor(cursor: str) -> TagCountCursor:
    """
    Base64 커서 문자열을 태그 수 커서로 디코딩

    Args:
        cursor: Base64 인코딩된 커서 문자열

    Returns:
        태그 수 커서 데이터

    Raises:
        CursorDecodeError: 잘못된 커서 형식
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)

        return TagCountCursor(
            shared_tags_count=int(data["tc"]),
            exposure_score=float(data["exp"]),
            recipe_id=str(data["id"]),
        )
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise CursorDecodeError(f"잘못된 커서 형식: {e}") from e
