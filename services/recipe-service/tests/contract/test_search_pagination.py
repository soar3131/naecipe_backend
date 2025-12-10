"""
페이지네이션 Contract 테스트

커서 기반 페이지네이션 스키마 및 파라미터 검증
"""

import pytest
from pydantic import ValidationError

from recipe_service.schemas.search import SearchQueryParams, SearchResult
from recipe_service.utils.cursor import encode_cursor, decode_cursor, CursorError


class TestPaginationParamsContract:
    """페이지네이션 파라미터 Contract 테스트"""

    def test_default_limit(self):
        """기본 limit은 20"""
        params = SearchQueryParams()
        assert params.limit == 20

    def test_valid_limit_range(self):
        """유효한 limit 범위 (1-100)"""
        params = SearchQueryParams(limit=1)
        assert params.limit == 1

        params = SearchQueryParams(limit=50)
        assert params.limit == 50

        params = SearchQueryParams(limit=100)
        assert params.limit == 100

    def test_invalid_limit_range(self):
        """잘못된 limit 범위"""
        with pytest.raises(ValidationError):
            SearchQueryParams(limit=0)

        with pytest.raises(ValidationError):
            SearchQueryParams(limit=-1)

        with pytest.raises(ValidationError):
            SearchQueryParams(limit=101)

    def test_cursor_optional(self):
        """cursor는 선택적"""
        params = SearchQueryParams()
        assert params.cursor is None

    def test_valid_cursor(self):
        """유효한 cursor"""
        params = SearchQueryParams(cursor="abc123xyz")
        assert params.cursor == "abc123xyz"

    def test_cursor_max_length(self):
        """cursor 최대 길이 (200자)"""
        cursor_200 = "a" * 200
        params = SearchQueryParams(cursor=cursor_200)
        assert len(params.cursor) == 200

        with pytest.raises(ValidationError):
            SearchQueryParams(cursor="a" * 201)


class TestCursorEncodingContract:
    """커서 인코딩/디코딩 Contract 테스트"""

    def test_encode_decode_roundtrip(self):
        """인코딩 후 디코딩하면 원본 복원"""
        sort = "relevance"
        value = 85.5
        recipe_id = "recipe-123"

        cursor = encode_cursor(sort, value, recipe_id)
        decoded_sort, decoded_value, decoded_id = decode_cursor(cursor)

        assert decoded_sort == sort
        assert decoded_value == value
        assert decoded_id == recipe_id

    def test_encode_decode_datetime(self):
        """datetime 인코딩/디코딩"""
        from datetime import datetime, timezone

        sort = "latest"
        value = datetime(2024, 12, 10, 12, 0, 0, tzinfo=timezone.utc)
        recipe_id = "recipe-456"

        cursor = encode_cursor(sort, value, recipe_id)
        decoded_sort, decoded_value, decoded_id = decode_cursor(cursor)

        assert decoded_sort == sort
        assert decoded_value == value.isoformat()
        assert decoded_id == recipe_id

    def test_encode_decode_integer(self):
        """정수 인코딩/디코딩"""
        sort = "cook_time"
        value = 30
        recipe_id = "recipe-789"

        cursor = encode_cursor(sort, value, recipe_id)
        decoded_sort, decoded_value, decoded_id = decode_cursor(cursor)

        assert decoded_sort == sort
        assert decoded_value == value
        assert decoded_id == recipe_id

    def test_invalid_cursor_format(self):
        """잘못된 커서 형식"""
        with pytest.raises(CursorError):
            decode_cursor("invalid-cursor")

        with pytest.raises(CursorError):
            decode_cursor("")

        with pytest.raises(CursorError):
            decode_cursor("not-base64!")


class TestSearchResultPaginationContract:
    """SearchResult 페이지네이션 필드 Contract 테스트"""

    def test_first_page_result(self):
        """첫 페이지 결과"""
        result = SearchResult(
            items=[],
            next_cursor="cursor123",
            has_more=True,
        )
        assert result.next_cursor == "cursor123"
        assert result.has_more is True

    def test_last_page_result(self):
        """마지막 페이지 결과"""
        result = SearchResult(
            items=[],
            next_cursor=None,
            has_more=False,
        )
        assert result.next_cursor is None
        assert result.has_more is False

    def test_total_count_always_null(self):
        """total_count는 항상 None (성능 최적화)"""
        result = SearchResult(
            items=[],
            has_more=False,
        )
        assert result.total_count is None

    def test_has_more_indicates_next_page(self):
        """has_more가 True면 next_cursor 존재"""
        result = SearchResult(
            items=[],
            next_cursor="abc",
            has_more=True,
        )
        assert result.has_more is True
        assert result.next_cursor is not None


class TestCursorSortConsistencyContract:
    """커서와 정렬 기준 일관성 Contract 테스트"""

    def test_cursor_contains_sort_info(self):
        """커서에 정렬 정보 포함"""
        cursor = encode_cursor("latest", "2024-12-10T12:00:00", "recipe-1")
        sort, value, id = decode_cursor(cursor)
        assert sort == "latest"

    def test_different_sort_different_cursor(self):
        """다른 정렬은 다른 커서"""
        cursor_relevance = encode_cursor("relevance", 85.5, "recipe-1")
        cursor_latest = encode_cursor("latest", "2024-12-10T12:00:00", "recipe-1")

        assert cursor_relevance != cursor_latest
