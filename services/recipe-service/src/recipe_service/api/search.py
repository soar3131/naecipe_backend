"""
검색 API 라우터

레시피 검색 엔드포인트를 정의합니다.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from recipe_service.database import get_session
from recipe_service.schemas.search import SearchQueryParams, SearchResult
from recipe_service.services.search_service import SearchService
from recipe_service.utils.cursor import CursorError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["search"])


@router.get(
    "/search",
    response_model=SearchResult,
    summary="레시피 검색",
    description="""
레시피를 검색합니다.

**검색 대상**:
- 레시피 제목
- 레시피 설명
- 재료명
- 요리사명

**필터**:
- `difficulty`: 난이도 (easy, medium, hard)
- `max_cook_time`: 최대 조리시간 (분)
- `tag`: 태그명
- `chef_id`: 요리사 ID

**정렬**:
- `relevance`: 관련도순 (기본값)
- `latest`: 최신순
- `cook_time`: 조리시간순
- `popularity`: 인기순

**페이지네이션**:
커서 기반 페이지네이션을 사용합니다.
`next_cursor`를 다음 요청의 `cursor` 파라미터로 전달하세요.
""",
)
async def search_recipes(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[
        str | None,
        Query(max_length=100, description="검색 키워드"),
    ] = None,
    difficulty: Annotated[
        str | None,
        Query(
            pattern="^(easy|medium|hard)$",
            description="난이도 필터",
        ),
    ] = None,
    max_cook_time: Annotated[
        int | None,
        Query(ge=1, le=1440, description="최대 조리시간 (분)"),
    ] = None,
    tag: Annotated[
        str | None,
        Query(max_length=50, description="태그 필터"),
    ] = None,
    chef_id: Annotated[
        UUID | None,
        Query(description="요리사 ID 필터"),
    ] = None,
    sort: Annotated[
        str,
        Query(
            pattern="^(relevance|latest|cook_time|popularity)$",
            description="정렬 기준",
        ),
    ] = "relevance",
    cursor: Annotated[
        str | None,
        Query(max_length=200, description="페이지네이션 커서"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="결과 개수"),
    ] = 20,
) -> SearchResult:
    """레시피 검색 API"""
    params = SearchQueryParams(
        q=q,
        difficulty=difficulty,
        max_cook_time=max_cook_time,
        tag=tag,
        chef_id=chef_id,
        sort=sort,
        cursor=cursor,
        limit=limit,
    )

    try:
        service = SearchService(session)
        return await service.search(params)
    except CursorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="검색 처리 중 오류가 발생했습니다",
        )
