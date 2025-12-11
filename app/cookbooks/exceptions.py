"""
Cookbooks 모듈 예외

레시피북 관련 커스텀 예외를 정의합니다.
"""

from app.core.exceptions import ERROR_BASE_URI, ProblemDetail


class CookbookNotFoundError(ProblemDetail):
    """레시피북을 찾을 수 없음 (404)"""

    def __init__(
        self, cookbook_id: str | None = None, instance: str | None = None
    ) -> None:
        detail = "레시피북을 찾을 수 없습니다"
        if cookbook_id:
            detail = f"레시피북(ID: {cookbook_id})을 찾을 수 없습니다"
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/cookbook/not-found",
            title="Cookbook Not Found",
            status=404,
            detail=detail,
            instance=instance,
        )


class CannotDeleteDefaultCookbookError(ProblemDetail):
    """기본 레시피북 삭제 불가 (400)"""

    def __init__(self, instance: str | None = None) -> None:
        super().__init__(
            type_uri=f"{ERROR_BASE_URI}/cookbook/cannot-delete-default",
            title="Cannot Delete Default Cookbook",
            status=400,
            detail="기본 레시피북은 삭제할 수 없습니다",
            instance=instance,
            extensions={"code": "CANNOT_DELETE_DEFAULT_COOKBOOK"},
        )
