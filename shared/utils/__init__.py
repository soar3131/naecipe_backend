"""
Shared Utils 패키지

공통 유틸리티 함수들을 제공합니다.
"""

from shared.utils.pagination import (
    CursorDecodeError,
    SimilarityCursor,
    TagCountCursor,
    ViewCountCursor,
    decode_similarity_cursor,
    decode_tag_count_cursor,
    decode_view_count_cursor,
    encode_similarity_cursor,
    encode_tag_count_cursor,
    encode_view_count_cursor,
)

__all__ = [
    # Exceptions
    "CursorDecodeError",
    # Similarity Cursor
    "SimilarityCursor",
    "encode_similarity_cursor",
    "decode_similarity_cursor",
    # View Count Cursor
    "ViewCountCursor",
    "encode_view_count_cursor",
    "decode_view_count_cursor",
    # Tag Count Cursor
    "TagCountCursor",
    "encode_tag_count_cursor",
    "decode_tag_count_cursor",
]
