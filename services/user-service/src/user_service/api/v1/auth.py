"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.api.deps import CurrentUser, DBSession, get_current_user
from user_service.core.security import decode_token
from user_service.db.session import get_db
from user_service.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from user_service.schemas.user import RegisterResponse, UserResponse
from user_service.services.auth import AuthService
from user_service.services.user import UserService

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="사용자 회원가입",
    description="이메일과 비밀번호로 새 사용자 계정을 생성합니다.",
    responses={
        201: {"description": "회원가입 성공"},
        409: {"description": "이미 존재하는 이메일"},
        422: {"description": "유효하지 않은 요청"},
    },
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user with email and password

    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters with letters and numbers
    """
    user_service = UserService(db)
    return await user_service.create_user(request)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="사용자 로그인",
    description="이메일과 비밀번호로 로그인하여 JWT 토큰을 발급받습니다.",
    responses={
        200: {"description": "로그인 성공"},
        401: {"description": "인증 실패"},
        423: {"description": "계정 잠금"},
    },
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Login with email and password

    - **email**: Registered email address
    - **password**: User password

    Returns access and refresh tokens.
    Account locks after 5 failed attempts for 15 minutes.
    """
    auth_service = AuthService(db)
    return await auth_service.login(request.email, request.password)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="현재 사용자 정보",
    description="현재 로그인한 사용자의 정보를 조회합니다.",
    responses={
        200: {"description": "조회 성공"},
        401: {"description": "인증 필요"},
    },
)
async def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """Get current authenticated user information

    Requires valid access token in Authorization header.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        status=current_user.status.value,
        created_at=current_user.created_at,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="토큰 갱신",
    description="Refresh Token으로 새로운 Access Token을 발급받습니다.",
    responses={
        200: {"description": "갱신 성공"},
        401: {"description": "유효하지 않은 토큰"},
    },
)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token

    - **refresh_token**: Valid refresh token from login

    Returns new access and refresh tokens (token rotation).
    """
    auth_service = AuthService(db)
    return await auth_service.refresh_token(request.refresh_token)


security = HTTPBearer()


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="현재 세션을 종료하고 토큰을 무효화합니다.",
    responses={
        204: {"description": "로그아웃 성공"},
        401: {"description": "인증 필요"},
    },
)
async def logout(
    current_user: CurrentUser,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Logout and invalidate tokens

    Blacklists current access token and deletes refresh token session.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload:
        auth_service = AuthService(db)
        await auth_service.logout(
            user_id=str(current_user.id),
            token_jti=payload.get("jti", ""),
            token_exp=payload.get("exp", 0),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
