"""
필터링 Contract 테스트

필터 파라미터 검증 및 스키마 테스트
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from recipe_service.schemas.search import SearchQueryParams


class TestFilterParamsContract:
    """필터 파라미터 Contract 테스트"""

    def test_difficulty_filter_valid_values(self):
        """난이도 필터 유효값 테스트"""
        for difficulty in ["easy", "medium", "hard"]:
            params = SearchQueryParams(difficulty=difficulty)
            assert params.difficulty == difficulty

    def test_difficulty_filter_invalid_value(self):
        """난이도 필터 잘못된 값 테스트"""
        with pytest.raises(ValidationError):
            SearchQueryParams(difficulty="expert")

        with pytest.raises(ValidationError):
            SearchQueryParams(difficulty="beginner")

    def test_max_cook_time_filter_valid_range(self):
        """최대 조리시간 유효 범위 (1-1440분)"""
        params = SearchQueryParams(max_cook_time=1)
        assert params.max_cook_time == 1

        params = SearchQueryParams(max_cook_time=60)
        assert params.max_cook_time == 60

        params = SearchQueryParams(max_cook_time=1440)
        assert params.max_cook_time == 1440

    def test_max_cook_time_filter_invalid_range(self):
        """최대 조리시간 잘못된 범위"""
        with pytest.raises(ValidationError):
            SearchQueryParams(max_cook_time=0)

        with pytest.raises(ValidationError):
            SearchQueryParams(max_cook_time=-1)

        with pytest.raises(ValidationError):
            SearchQueryParams(max_cook_time=1441)

    def test_tag_filter_valid(self):
        """태그 필터 유효값"""
        params = SearchQueryParams(tag="한식")
        assert params.tag == "한식"

        params = SearchQueryParams(tag="Korean Food")
        assert params.tag == "Korean Food"

    def test_tag_filter_max_length(self):
        """태그 필터 최대 길이 (50자)"""
        tag_50 = "a" * 50
        params = SearchQueryParams(tag=tag_50)
        assert params.tag == tag_50

        with pytest.raises(ValidationError):
            SearchQueryParams(tag="a" * 51)

    def test_chef_id_filter_valid_uuid(self):
        """요리사 ID 필터 유효 UUID"""
        chef_id = uuid4()
        params = SearchQueryParams(chef_id=chef_id)
        assert params.chef_id == chef_id

    def test_chef_id_filter_invalid_uuid(self):
        """요리사 ID 필터 잘못된 UUID"""
        with pytest.raises(ValidationError):
            SearchQueryParams(chef_id="invalid-uuid")

        with pytest.raises(ValidationError):
            SearchQueryParams(chef_id="12345")


class TestFilterCombinationsContract:
    """필터 조합 Contract 테스트"""

    def test_multiple_filters_combination(self):
        """복수 필터 조합"""
        chef_id = uuid4()
        params = SearchQueryParams(
            q="김치",
            difficulty="easy",
            max_cook_time=30,
            tag="한식",
            chef_id=chef_id,
        )

        assert params.q == "김치"
        assert params.difficulty == "easy"
        assert params.max_cook_time == 30
        assert params.tag == "한식"
        assert params.chef_id == chef_id

    def test_filter_with_sort(self):
        """필터와 정렬 조합"""
        params = SearchQueryParams(
            difficulty="medium",
            sort="cook_time",
        )

        assert params.difficulty == "medium"
        assert params.sort == "cook_time"

    def test_filter_with_pagination(self):
        """필터와 페이지네이션 조합"""
        params = SearchQueryParams(
            max_cook_time=60,
            cursor="abc123",
            limit=50,
        )

        assert params.max_cook_time == 60
        assert params.cursor == "abc123"
        assert params.limit == 50

    def test_all_filters_with_all_options(self):
        """모든 필터와 모든 옵션 조합"""
        chef_id = uuid4()
        params = SearchQueryParams(
            q="불고기",
            difficulty="hard",
            max_cook_time=120,
            tag="고기요리",
            chef_id=chef_id,
            sort="popularity",
            cursor="xyz789",
            limit=10,
        )

        assert params.q == "불고기"
        assert params.difficulty == "hard"
        assert params.max_cook_time == 120
        assert params.tag == "고기요리"
        assert params.chef_id == chef_id
        assert params.sort == "popularity"
        assert params.cursor == "xyz789"
        assert params.limit == 10


class TestEmptyResultContract:
    """빈 결과 Contract 테스트"""

    def test_no_filters_returns_valid_params(self):
        """필터 없이 유효한 파라미터 반환"""
        params = SearchQueryParams()

        assert params.q is None
        assert params.difficulty is None
        assert params.max_cook_time is None
        assert params.tag is None
        assert params.chef_id is None
        assert params.sort == "relevance"
        assert params.cursor is None
        assert params.limit == 20

    def test_only_keyword_valid(self):
        """키워드만 있어도 유효"""
        params = SearchQueryParams(q="테스트")
        assert params.q == "테스트"

    def test_only_filter_valid(self):
        """필터만 있어도 유효"""
        params = SearchQueryParams(difficulty="easy")
        assert params.difficulty == "easy"
        assert params.q is None
