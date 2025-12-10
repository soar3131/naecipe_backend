"""
캐싱 Contract 테스트

캐시 키 생성 및 캐싱 동작 스키마 검증
데이터베이스 의존성 없이 순수 로직 테스트
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from recipe_service.schemas.search import SearchQueryParams, SearchResult, SearchResultItem
from recipe_service.services.search_service import SearchService


class TestCacheKeyGenerationContract:
    """캐시 키 생성 Contract 테스트"""

    @pytest.fixture
    def mock_session(self):
        """Mock 세션"""
        return MagicMock()

    def test_same_params_same_key(self, mock_session):
        """동일한 파라미터는 동일한 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", difficulty="easy", sort="latest")
        params2 = SearchQueryParams(q="김치", difficulty="easy", sort="latest")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 == key2

    def test_different_keyword_different_key(self, mock_session):
        """다른 키워드는 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", sort="latest")
        params2 = SearchQueryParams(q="된장", sort="latest")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_sort_different_key(self, mock_session):
        """다른 정렬 옵션은 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", sort="latest")
        params2 = SearchQueryParams(q="김치", sort="relevance")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_cursor_different_key(self, mock_session):
        """다른 커서는 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", cursor=None)
        params2 = SearchQueryParams(q="김치", cursor="cursor123")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_limit_different_key(self, mock_session):
        """다른 limit은 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", limit=10)
        params2 = SearchQueryParams(q="김치", limit=20)

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_difficulty_different_key(self, mock_session):
        """다른 난이도 필터는 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", difficulty="easy")
        params2 = SearchQueryParams(q="김치", difficulty="hard")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_cook_time_different_key(self, mock_session):
        """다른 조리시간 필터는 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", max_cook_time=30)
        params2 = SearchQueryParams(q="김치", max_cook_time=60)

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_different_tag_different_key(self, mock_session):
        """다른 태그 필터는 다른 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams(q="김치", tag="한식")
        params2 = SearchQueryParams(q="김치", tag="중식")

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 != key2

    def test_cache_key_format(self, mock_session):
        """캐시 키 형식 확인"""
        service = SearchService(mock_session)

        params = SearchQueryParams(q="테스트")
        key = service._get_search_cache_key(params)

        # "search:recipes:" 접두사 + 16자리 해시
        assert key.startswith("search:recipes:")
        assert len(key) == len("search:recipes:") + 16

    def test_cache_key_is_deterministic(self, mock_session):
        """캐시 키 생성은 결정적"""
        service = SearchService(mock_session)

        params = SearchQueryParams(
            q="김치찌개",
            difficulty="medium",
            max_cook_time=45,
            tag="한식",
            sort="popularity",
            limit=25,
        )

        keys = [service._get_search_cache_key(params) for _ in range(5)]

        # 모든 키가 동일해야 함
        assert len(set(keys)) == 1

    def test_empty_params_consistent_key(self, mock_session):
        """빈 파라미터도 일관된 캐시 키"""
        service = SearchService(mock_session)

        params1 = SearchQueryParams()
        params2 = SearchQueryParams()

        key1 = service._get_search_cache_key(params1)
        key2 = service._get_search_cache_key(params2)

        assert key1 == key2


class TestSearchResultCacheableContract:
    """SearchResult 캐시 가능 여부 Contract 테스트"""

    def test_search_result_serializable(self):
        """SearchResult는 JSON 직렬화 가능"""
        result = SearchResult(
            items=[
                SearchResultItem(
                    id="recipe-1",
                    title="테스트 레시피",
                    description="테스트 설명",
                    thumbnail_url=None,
                    prep_time_minutes=10,
                    cook_time_minutes=30,
                    difficulty="easy",
                    exposure_score=85.0,
                    chef=None,
                    tags=[],
                    created_at=datetime.now(timezone.utc),
                )
            ],
            next_cursor="cursor123",
            has_more=True,
        )

        # JSON 직렬화 가능해야 함
        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "recipe-1" in json_str
        assert "테스트 레시피" in json_str

    def test_search_result_deserializable(self):
        """SearchResult는 JSON 역직렬화 가능"""
        original = SearchResult(
            items=[
                SearchResultItem(
                    id="recipe-1",
                    title="테스트 레시피",
                    description="테스트 설명",
                    thumbnail_url="https://example.com/img.jpg",
                    prep_time_minutes=10,
                    cook_time_minutes=30,
                    difficulty="easy",
                    exposure_score=85.0,
                    chef=None,
                    tags=[],
                    created_at=datetime(2024, 12, 10, 12, 0, 0, tzinfo=timezone.utc),
                )
            ],
            next_cursor="cursor123",
            has_more=True,
        )

        # 직렬화 후 역직렬화
        json_str = original.model_dump_json()
        restored = SearchResult.model_validate_json(json_str)

        assert len(restored.items) == 1
        assert restored.items[0].id == "recipe-1"
        assert restored.items[0].title == "테스트 레시피"
        assert restored.next_cursor == "cursor123"
        assert restored.has_more is True

    def test_empty_result_serializable(self):
        """빈 검색 결과도 직렬화 가능"""
        result = SearchResult(
            items=[],
            next_cursor=None,
            has_more=False,
        )

        json_str = result.model_dump_json()
        restored = SearchResult.model_validate_json(json_str)

        assert restored.items == []
        assert restored.next_cursor is None
        assert restored.has_more is False


class TestCacheTTLContract:
    """캐시 TTL Contract 테스트"""

    def test_cache_ttl_configured(self):
        """캐시 TTL이 설정에 정의됨"""
        from recipe_service.core.config import get_settings

        settings = get_settings()
        assert hasattr(settings.redis, 'SEARCH_CACHE_TTL')
        assert settings.redis.SEARCH_CACHE_TTL > 0

    def test_cache_ttl_default_value(self):
        """캐시 TTL 기본값은 300초 (5분)"""
        from recipe_service.core.config import RedisSettings

        redis_settings = RedisSettings()
        assert redis_settings.SEARCH_CACHE_TTL == 300
