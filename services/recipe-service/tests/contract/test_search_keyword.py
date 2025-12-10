"""
키워드 검색 Contract 테스트

검색 API 응답 스키마 및 동작 검증
- 검색어 매칭
- 빈 결과 처리
- 특수문자 처리
"""

import pytest
from pydantic import ValidationError

from recipe_service.schemas.search import (
    ChefSummary,
    SearchQueryParams,
    SearchResult,
    SearchResultItem,
    TagSummary,
)


class TestSearchQueryParamsContract:
    """SearchQueryParams 스키마 Contract 테스트"""

    def test_default_values(self):
        """기본값 검증"""
        params = SearchQueryParams()
        assert params.q is None
        assert params.difficulty is None
        assert params.max_cook_time is None
        assert params.tag is None
        assert params.chef_id is None
        assert params.sort == "relevance"
        assert params.cursor is None
        assert params.limit == 20

    def test_keyword_sanitization(self):
        """검색어 정규화 검증"""
        # 앞뒤 공백 제거
        params = SearchQueryParams(q="  김치  ")
        assert params.q == "김치"

        # 연속 공백 → 단일 공백
        params = SearchQueryParams(q="김치   찌개")
        assert params.q == "김치 찌개"

        # 빈 문자열 → None
        params = SearchQueryParams(q="   ")
        assert params.q is None

    def test_keyword_max_length(self):
        """검색어 최대 길이 검증 (100자)"""
        long_keyword = "a" * 100
        params = SearchQueryParams(q=long_keyword)
        assert len(params.q) == 100

        # 101자 초과 시 ValidationError
        with pytest.raises(ValidationError):
            SearchQueryParams(q="a" * 101)

    def test_difficulty_validation(self):
        """난이도 검증"""
        for difficulty in ["easy", "medium", "hard"]:
            params = SearchQueryParams(difficulty=difficulty)
            assert params.difficulty == difficulty

        # 잘못된 값
        with pytest.raises(ValidationError):
            SearchQueryParams(difficulty="expert")

    def test_max_cook_time_validation(self):
        """최대 조리시간 검증 (1-1440분)"""
        params = SearchQueryParams(max_cook_time=1)
        assert params.max_cook_time == 1

        params = SearchQueryParams(max_cook_time=1440)
        assert params.max_cook_time == 1440

        with pytest.raises(ValidationError):
            SearchQueryParams(max_cook_time=0)

        with pytest.raises(ValidationError):
            SearchQueryParams(max_cook_time=1441)

    def test_sort_validation(self):
        """정렬 기준 검증"""
        for sort in ["relevance", "latest", "cook_time", "popularity"]:
            params = SearchQueryParams(sort=sort)
            assert params.sort == sort

        with pytest.raises(ValidationError):
            SearchQueryParams(sort="invalid")

    def test_limit_validation(self):
        """결과 개수 검증 (1-100)"""
        params = SearchQueryParams(limit=1)
        assert params.limit == 1

        params = SearchQueryParams(limit=100)
        assert params.limit == 100

        with pytest.raises(ValidationError):
            SearchQueryParams(limit=0)

        with pytest.raises(ValidationError):
            SearchQueryParams(limit=101)


class TestSearchResultContract:
    """SearchResult 응답 스키마 Contract 테스트"""

    def test_empty_result(self):
        """빈 결과 검증"""
        result = SearchResult(items=[], has_more=False)
        assert result.items == []
        assert result.next_cursor is None
        assert result.has_more is False
        assert result.total_count is None

    def test_result_with_items(self):
        """아이템이 있는 결과 검증"""
        from datetime import datetime

        item = SearchResultItem(
            id="recipe-1",
            title="김치찌개",
            description="맛있는 김치찌개",
            thumbnail_url="https://example.com/img.jpg",
            prep_time_minutes=10,
            cook_time_minutes=30,
            difficulty="easy",
            exposure_score=85.5,
            chef=ChefSummary(id="chef-1", name="백종원"),
            tags=[TagSummary(id="tag-1", name="한식")],
            created_at=datetime.now(),
        )

        result = SearchResult(
            items=[item],
            next_cursor="abc123",
            has_more=True,
        )

        assert len(result.items) == 1
        assert result.items[0].title == "김치찌개"
        assert result.next_cursor == "abc123"
        assert result.has_more is True
        assert result.total_count is None  # 항상 None

    def test_search_result_item_optional_fields(self):
        """SearchResultItem 선택 필드 검증"""
        from datetime import datetime

        # 필수 필드만으로 생성
        item = SearchResultItem(
            id="recipe-1",
            title="테스트",
            exposure_score=0.0,
            created_at=datetime.now(),
        )

        assert item.description is None
        assert item.thumbnail_url is None
        assert item.prep_time_minutes is None
        assert item.cook_time_minutes is None
        assert item.difficulty is None
        assert item.chef is None
        assert item.tags == []


class TestSpecialCharacterHandling:
    """특수문자 처리 테스트"""

    def test_korean_keywords(self):
        """한글 검색어 처리"""
        params = SearchQueryParams(q="김치찌개")
        assert params.q == "김치찌개"

    def test_mixed_language_keywords(self):
        """혼합 언어 검색어 처리"""
        params = SearchQueryParams(q="Pasta 파스타")
        assert params.q == "Pasta 파스타"

    def test_special_characters_in_keyword(self):
        """특수문자가 포함된 검색어 처리"""
        # SQL Injection 방지를 위해 서비스 레이어에서 처리
        # Contract에서는 스키마 통과 여부만 확인
        params = SearchQueryParams(q="김치's 찌개")
        assert "'" in params.q

    def test_numeric_keywords(self):
        """숫자 검색어 처리"""
        params = SearchQueryParams(q="10분 요리")
        assert params.q == "10분 요리"
