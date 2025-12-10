"""
정렬 Contract 테스트

정렬 파라미터 검증 및 스키마 테스트
"""

import pytest
from pydantic import ValidationError

from recipe_service.schemas.search import SearchQueryParams


class TestSortParamsContract:
    """정렬 파라미터 Contract 테스트"""

    def test_default_sort_is_relevance(self):
        """기본 정렬값은 relevance"""
        params = SearchQueryParams()
        assert params.sort == "relevance"

    def test_valid_sort_options(self):
        """유효한 정렬 옵션"""
        for sort in ["relevance", "latest", "cook_time", "popularity"]:
            params = SearchQueryParams(sort=sort)
            assert params.sort == sort

    def test_invalid_sort_option(self):
        """잘못된 정렬 옵션"""
        with pytest.raises(ValidationError):
            SearchQueryParams(sort="alphabetical")

        with pytest.raises(ValidationError):
            SearchQueryParams(sort="rating")

        with pytest.raises(ValidationError):
            SearchQueryParams(sort="random")

    def test_sort_case_sensitivity(self):
        """정렬 옵션 대소문자 구분"""
        # 소문자만 유효
        with pytest.raises(ValidationError):
            SearchQueryParams(sort="RELEVANCE")

        with pytest.raises(ValidationError):
            SearchQueryParams(sort="Latest")

    def test_sort_with_keyword(self):
        """키워드와 함께 정렬"""
        params = SearchQueryParams(q="김치", sort="latest")
        assert params.q == "김치"
        assert params.sort == "latest"

    def test_sort_with_filters(self):
        """필터와 함께 정렬"""
        params = SearchQueryParams(
            difficulty="easy",
            max_cook_time=30,
            sort="cook_time",
        )
        assert params.difficulty == "easy"
        assert params.max_cook_time == 30
        assert params.sort == "cook_time"

    def test_sort_with_pagination(self):
        """페이지네이션과 함께 정렬"""
        params = SearchQueryParams(
            sort="popularity",
            cursor="abc123",
            limit=50,
        )
        assert params.sort == "popularity"
        assert params.cursor == "abc123"
        assert params.limit == 50


class TestSortMeaningContract:
    """정렬 옵션 의미 Contract 테스트"""

    def test_relevance_sort_meaning(self):
        """relevance: 관련도순 (exposure_score 기반)"""
        params = SearchQueryParams(sort="relevance")
        # relevance는 exposure_score DESC, id DESC로 정렬
        assert params.sort == "relevance"

    def test_latest_sort_meaning(self):
        """latest: 최신순 (created_at 기반)"""
        params = SearchQueryParams(sort="latest")
        # latest는 created_at DESC, id DESC로 정렬
        assert params.sort == "latest"

    def test_cook_time_sort_meaning(self):
        """cook_time: 조리시간순 (cook_time_minutes 기반)"""
        params = SearchQueryParams(sort="cook_time")
        # cook_time은 cook_time_minutes ASC NULLS LAST, id ASC로 정렬
        assert params.sort == "cook_time"

    def test_popularity_sort_meaning(self):
        """popularity: 인기순 (view_count 기반)"""
        params = SearchQueryParams(sort="popularity")
        # popularity는 view_count DESC, id DESC로 정렬
        assert params.sort == "popularity"
