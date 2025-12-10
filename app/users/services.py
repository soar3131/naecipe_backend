"""
Users 모듈 서비스 레이어

인증, 사용자, 세션 관리 서비스를 정의합니다.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    EmailExistsError,
    InvalidTokenError,
    TokenRevokedError,
    UserNotFoundError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.infra.redis import get_redis
from app.users.models import OAuthAccount, OAuthProvider, TastePreference, User, UserProfile, UserStatus
from app.users.schemas import RegisterRequest, RegisterResponse, TokenResponse


# ==========================================================================
# Session Service
# ==========================================================================


class SessionService:
    """Redis 세션 관리 서비스"""

    # Key prefixes
    SESSION_PREFIX = "session:"
    BLACKLIST_PREFIX = "blacklist:"
    LOGIN_FAILURE_PREFIX = "login_failure:"

    @classmethod
    async def store_refresh_token(cls, user_id: str, refresh_token: str) -> None:
        """Redis에 리프레시 토큰 저장"""
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"
        expire_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await redis.set(key, refresh_token, ex=expire_seconds)

    @classmethod
    async def get_refresh_token(cls, user_id: str) -> str | None:
        """저장된 리프레시 토큰 조회"""
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"

        return await redis.get(key)

    @classmethod
    async def delete_session(cls, user_id: str) -> None:
        """세션 삭제 (로그아웃)"""
        redis = await get_redis()
        key = f"{cls.SESSION_PREFIX}{user_id}"

        await redis.delete(key)

    @classmethod
    async def blacklist_token(cls, token_jti: str, expires_in: int) -> None:
        """액세스 토큰 블랙리스트 추가"""
        redis = await get_redis()
        key = f"{cls.BLACKLIST_PREFIX}{token_jti}"

        await redis.set(key, "1", ex=expires_in)

    @classmethod
    async def is_token_blacklisted(cls, token_jti: str) -> bool:
        """토큰 블랙리스트 여부 확인"""
        redis = await get_redis()
        key = f"{cls.BLACKLIST_PREFIX}{token_jti}"

        return await redis.exists(key) > 0

    @classmethod
    async def get_login_failure_count(cls, email: str) -> int:
        """로그인 실패 횟수 조회"""
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"

        count = await redis.get(key)
        return int(count) if count else 0

    @classmethod
    async def increment_login_failure(cls, email: str) -> int:
        """로그인 실패 횟수 증가"""
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"
        expire_seconds = settings.ACCOUNT_LOCK_MINUTES * 60

        count = await redis.incr(key)
        await redis.expire(key, expire_seconds)

        return count

    @classmethod
    async def reset_login_failure(cls, email: str) -> None:
        """로그인 실패 횟수 초기화"""
        redis = await get_redis()
        key = f"{cls.LOGIN_FAILURE_PREFIX}{email.lower()}"

        await redis.delete(key)


# ==========================================================================
# User Service
# ==========================================================================


class UserService:
    """사용자 관리 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, request: RegisterRequest) -> RegisterResponse:
        """이메일/비밀번호로 새 사용자 생성"""
        email = request.email.lower()

        # 중복 이메일 확인
        if await self._email_exists(email):
            raise EmailExistsError()

        # 비밀번호 해싱
        password_hash = hash_password(request.password)

        # 사용자 생성
        user = User(
            email=email,
            password_hash=password_hash,
            status=UserStatus.ACTIVE,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        # 프로필 자동 생성
        profile = UserProfile(
            user_id=user.id,
            display_name="",
        )
        self.db.add(profile)
        await self.db.flush()

        return RegisterResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
        )

    async def _email_exists(self, email: str) -> bool:
        """이메일 존재 여부 확인 (대소문자 구분 안 함)"""
        result = await self.db.execute(
            select(User.id).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    async def get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: str) -> User | None:
        """ID로 사용자 조회"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


# ==========================================================================
# Auth Service
# ==========================================================================


class AuthService:
    """인증 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def login(self, email: str, password: str) -> TokenResponse:
        """사용자 인증 및 토큰 발급"""
        email = email.lower()

        # 계정 잠금 확인 (Redis 실패 카운터)
        failure_count = await SessionService.get_login_failure_count(email)
        if failure_count >= settings.LOGIN_FAILURE_LIMIT:
            raise AccountLockedError()

        # 사용자 조회
        user = await self._get_user_by_email(email)
        if not user:
            await self._handle_login_failure(email)
            raise AuthenticationError(detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        # 사용자 상태 확인
        if user.status == UserStatus.LOCKED:
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                raise AccountLockedError()
            # 잠금 만료, 상태 초기화
            user.status = UserStatus.ACTIVE
            user.locked_until = None

        if user.status != UserStatus.ACTIVE:
            await self._handle_login_failure(email)
            raise AuthenticationError(detail="비활성화된 계정입니다.")

        # 비밀번호 검증
        if not user.password_hash or not verify_password(
            password, user.password_hash
        ):
            await self._handle_login_failure(email)
            raise AuthenticationError(detail="이메일 또는 비밀번호가 올바르지 않습니다.")

        # 성공 시 실패 카운터 초기화
        await SessionService.reset_login_failure(email)

        # 토큰 생성
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id), jti=str(uuid4()))

        # 세션에 리프레시 토큰 저장
        await SessionService.store_refresh_token(str(user.id), refresh_token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """리프레시 토큰으로 액세스 토큰 갱신"""
        # 리프레시 토큰 검증
        payload = verify_refresh_token(refresh_token)
        if not payload:
            raise InvalidTokenError()

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        # 세션 존재 확인
        stored_token = await SessionService.get_refresh_token(user_id)
        if not stored_token or stored_token != refresh_token:
            raise TokenRevokedError()

        # 사용자 존재 확인
        user = await self._get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(detail="비활성화된 계정입니다.")

        # 새 토큰 생성 (토큰 로테이션)
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id, jti=str(uuid4()))

        # 새 리프레시 토큰으로 세션 갱신
        await SessionService.store_refresh_token(user_id, new_refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, user_id: str, token_jti: str, token_exp: int) -> None:
        """로그아웃 및 토큰 무효화"""
        # 세션 삭제 (리프레시 토큰 무효화)
        await SessionService.delete_session(user_id)

        # 현재 액세스 토큰 블랙리스트 추가
        expires_in = max(0, token_exp - int(datetime.now(timezone.utc).timestamp()))
        if expires_in > 0:
            await SessionService.blacklist_token(token_jti, expires_in)

    async def _get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> User | None:
        """ID로 사용자 조회"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _handle_login_failure(self, email: str) -> None:
        """로그인 실패 처리 - 카운터 증가 및 필요시 잠금"""
        failure_count = await SessionService.increment_login_failure(email)

        # 임계값 도달 시 DB에서 계정 잠금
        if failure_count >= settings.LOGIN_FAILURE_LIMIT:
            user = await self._get_user_by_email(email)
            if user:
                user.status = UserStatus.LOCKED
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.ACCOUNT_LOCK_MINUTES
                )
                await self.db.flush()


# ==========================================================================
# Profile Service
# ==========================================================================


class ProfileService:
    """사용자 프로필 관리 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: str) -> "ProfileData | None":
        """사용자 프로필 조회"""
        from app.users.schemas import ProfileData

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        profile = user.profile
        if not profile:
            profile = await self._create_default_profile(user_id)

        return ProfileData(
            id=user.id,
            email=user.email,
            displayName=profile.display_name or user.email.split("@")[0],
            profileImageUrl=profile.profile_image_url,
            createdAt=user.created_at,
            updatedAt=profile.updated_at,
        )

    async def update_profile(
        self,
        user_id: str,
        data: "ProfileUpdateRequest",
    ) -> "ProfileData | None":
        """사용자 프로필 수정"""
        from app.users.schemas import ProfileData

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        profile = user.profile
        if not profile:
            profile = await self._create_default_profile(user_id)

        if data.display_name is not None:
            profile.display_name = data.display_name
        if data.profile_image_url is not None:
            profile.profile_image_url = data.profile_image_url

        await self.db.flush()
        await self.db.refresh(profile)

        return ProfileData(
            id=user.id,
            email=user.email,
            displayName=profile.display_name or user.email.split("@")[0],
            profileImageUrl=profile.profile_image_url,
            createdAt=user.created_at,
            updatedAt=profile.updated_at,
        )

    async def _create_default_profile(self, user_id: str) -> UserProfile:
        """기본 프로필 생성"""
        profile = UserProfile(
            user_id=user_id,
            display_name="",
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def ensure_profile_exists(self, user_id: str) -> UserProfile:
        """프로필 존재 보장 (없으면 생성)"""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = await self._create_default_profile(user_id)

        return profile


# ==========================================================================
# Preference Service
# ==========================================================================


class PreferenceService:
    """사용자 취향 설정 관리 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_preferences(self, user_id: str) -> "PreferencesData | None":
        """사용자 취향 설정 조회"""
        from app.users.schemas import PreferencesData, TastePreferenceData

        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        taste_result = await self.db.execute(
            select(TastePreference).where(TastePreference.user_id == user_id)
        )
        taste_prefs = taste_result.scalars().all()

        taste_dict = {}
        for pref in taste_prefs:
            taste_dict[pref.category] = TastePreferenceData(
                sweetness=pref.sweetness,
                saltiness=pref.saltiness,
                spiciness=pref.spiciness,
                sourness=pref.sourness,
            )

        return PreferencesData(
            dietaryRestrictions=profile.dietary_restrictions or [],
            allergies=profile.allergies or [],
            cuisinePreferences=profile.cuisine_preferences or [],
            skillLevel=profile.skill_level,
            householdSize=profile.household_size,
            tastePreferences=taste_dict,
            updatedAt=profile.updated_at,
        )

    async def update_preferences(
        self,
        user_id: str,
        data: "PreferencesUpdateRequest",
    ) -> "PreferencesData | None":
        """사용자 취향 설정 수정"""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        if data.dietary_restrictions is not None:
            profile.dietary_restrictions = [d.value for d in data.dietary_restrictions]
        if data.allergies is not None:
            profile.allergies = [a.value for a in data.allergies]
        if data.cuisine_preferences is not None:
            profile.cuisine_preferences = [c.value for c in data.cuisine_preferences]
        if data.skill_level is not None:
            profile.skill_level = data.skill_level
        if data.household_size is not None:
            profile.household_size = data.household_size

        if data.taste_preferences is not None:
            await self._update_taste_preferences(user_id, data.taste_preferences)

        await self.db.flush()
        await self.db.refresh(profile)

        return await self.get_preferences(user_id)

    async def _update_taste_preferences(
        self,
        user_id: str,
        taste_data: dict,
    ) -> None:
        """맛 취향 업데이트"""
        from app.users.schemas import TasteValues

        existing_result = await self.db.execute(
            select(TastePreference).where(TastePreference.user_id == user_id)
        )
        existing_prefs = {p.category: p for p in existing_result.scalars().all()}

        overall_values = taste_data.get("overall")

        for category, values in taste_data.items():
            if category in existing_prefs:
                pref = existing_prefs[category]
                self._apply_taste_values(pref, values, overall_values, category != "overall")
            else:
                pref = TastePreference(
                    user_id=user_id,
                    category=category,
                )
                self._apply_taste_values(pref, values, overall_values, category != "overall")
                self.db.add(pref)

    def _apply_taste_values(
        self,
        pref: TastePreference,
        values: "TasteValues",
        overall_values: "TasteValues | None",
        inherit_overall: bool,
    ) -> None:
        """맛 취향 값 적용"""
        if values.sweetness is not None:
            pref.sweetness = values.sweetness
        elif inherit_overall and overall_values and overall_values.sweetness is not None:
            pref.sweetness = overall_values.sweetness

        if values.saltiness is not None:
            pref.saltiness = values.saltiness
        elif inherit_overall and overall_values and overall_values.saltiness is not None:
            pref.saltiness = overall_values.saltiness

        if values.spiciness is not None:
            pref.spiciness = values.spiciness
        elif inherit_overall and overall_values and overall_values.spiciness is not None:
            pref.spiciness = overall_values.spiciness

        if values.sourness is not None:
            pref.sourness = values.sourness
        elif inherit_overall and overall_values and overall_values.sourness is not None:
            pref.sourness = overall_values.sourness


# ==========================================================================
# OAuth Service
# ==========================================================================


class OAuthService:
    """OAuth 소셜 로그인 서비스"""

    OAUTH_STATE_PREFIX = "oauth_state:"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_authorization_url(
        self, provider: "OAuthProviderEnum"
    ) -> "OAuthAuthorizationResponse":
        """OAuth 인증 URL 생성"""
        import secrets
        from app.users.oauth_providers import OAuthProviders
        from app.users.schemas import OAuthAuthorizationResponse

        config = OAuthProviders.get(provider)

        state = secrets.token_urlsafe(32)

        redis = await get_redis()
        state_key = f"{self.OAUTH_STATE_PREFIX}{state}"
        await redis.set(
            state_key,
            provider.value,
            ex=settings.OAUTH_STATE_EXPIRE_SECONDS,
        )

        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        if config.scopes:
            params["scope"] = " ".join(config.scopes)

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        authorization_url = f"{config.authorization_url}?{query_string}"

        return OAuthAuthorizationResponse(
            authorization_url=authorization_url,
            state=state,
        )

    async def handle_callback(
        self, provider: "OAuthProviderEnum", code: str, state: str
    ) -> "OAuthLoginResponse":
        """OAuth 콜백 처리"""
        from app.users.schemas import OAuthLoginResponse, OAuthUserInfo

        await self._validate_state(state, provider)
        oauth_token = await self._exchange_code_for_token(provider, code)
        oauth_user_data = await self._get_user_info(provider, oauth_token)
        user, oauth_account, is_new_user = await self._find_or_create_user(oauth_user_data)

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id), jti=str(uuid4()))

        await SessionService.store_refresh_token(str(user.id), refresh_token)

        return OAuthLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=OAuthUserInfo(
                id=str(user.id),
                email=user.email,
                provider=provider,
                created_at=user.created_at,
            ),
            is_new_user=is_new_user,
        )

    async def link_account(
        self, user_id: str, provider: "OAuthProviderEnum", code: str, state: str
    ) -> OAuthAccount:
        """기존 사용자에 OAuth 계정 연동"""
        from app.core.exceptions import OAuthAccountAlreadyLinkedError

        await self._validate_state(state, provider)
        oauth_token = await self._exchange_code_for_token(provider, code)
        oauth_user_data = await self._get_user_info(provider, oauth_token)

        existing_oauth = await self._get_oauth_account_by_provider_user_id(
            provider, oauth_user_data.provider_user_id
        )
        if existing_oauth:
            raise OAuthAccountAlreadyLinkedError(provider=provider.value)

        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=OAuthProvider(provider.value),
            provider_user_id=oauth_user_data.provider_user_id,
            provider_email=oauth_user_data.email,
        )
        self.db.add(oauth_account)
        await self.db.flush()

        return oauth_account

    async def _validate_state(self, state: str, expected_provider: "OAuthProviderEnum") -> None:
        """OAuth state 검증"""
        from app.core.exceptions import OAuthStateError

        redis = await get_redis()
        state_key = f"{self.OAUTH_STATE_PREFIX}{state}"

        stored_provider = await redis.get(state_key)
        if not stored_provider:
            raise OAuthStateError()

        await redis.delete(state_key)

        if stored_provider != expected_provider.value:
            raise OAuthStateError()

    async def _exchange_code_for_token(
        self, provider: "OAuthProviderEnum", code: str
    ) -> str:
        """인가 코드를 액세스 토큰으로 교환"""
        import httpx
        from app.core.exceptions import OAuthProviderError
        from app.users.oauth_providers import OAuthProviders

        config = OAuthProviders.get(provider)

        data = {
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    config.token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )
                response.raise_for_status()

                token_data = response.json()
                access_token = token_data.get("access_token")

                if not access_token:
                    raise OAuthProviderError(
                        provider=provider.value,
                        detail="액세스 토큰을 받지 못했습니다.",
                    )

                return access_token

            except httpx.HTTPStatusError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"토큰 교환 실패: {e.response.status_code}",
                )
            except httpx.RequestError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"네트워크 오류: {str(e)}",
                )

    async def _get_user_info(
        self, provider: "OAuthProviderEnum", access_token: str
    ) -> "OAuthUserData":
        """OAuth 제공자로부터 사용자 정보 조회"""
        import httpx
        from app.core.exceptions import OAuthProviderError
        from app.users.oauth_providers import OAuthProviders, parse_user_info
        from app.users.schemas import OAuthUserData

        config = OAuthProviders.get(provider)
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    config.user_info_url,
                    headers=headers,
                    timeout=10.0,
                )
                response.raise_for_status()

                raw_data = response.json()
                parsed_data = parse_user_info(provider, raw_data)

                return OAuthUserData(
                    provider=provider,
                    provider_user_id=parsed_data["provider_user_id"],
                    email=parsed_data.get("email", ""),
                    name=parsed_data.get("name"),
                    profile_image=parsed_data.get("profile_image"),
                )

            except httpx.HTTPStatusError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"사용자 정보 조회 실패: {e.response.status_code}",
                )
            except httpx.RequestError as e:
                raise OAuthProviderError(
                    provider=provider.value,
                    detail=f"네트워크 오류: {str(e)}",
                )

    async def _find_or_create_user(
        self, oauth_data: "OAuthUserData"
    ) -> tuple[User, OAuthAccount, bool]:
        """사용자 조회 또는 생성"""
        is_new_user = False

        oauth_account = await self._get_oauth_account_by_provider_user_id(
            oauth_data.provider, oauth_data.provider_user_id
        )
        if oauth_account:
            user = await self._get_user_by_id(oauth_account.user_id)
            return user, oauth_account, is_new_user

        user = None
        if oauth_data.email:
            user = await self._get_user_by_email(oauth_data.email)

        if not user:
            user = User(
                email=oauth_data.email or f"{oauth_data.provider_user_id}@{oauth_data.provider.value}.oauth",
                password_hash=None,
                status=UserStatus.ACTIVE,
            )
            self.db.add(user)
            await self.db.flush()
            is_new_user = True

            profile = UserProfile(
                user_id=str(user.id),
                display_name="",
            )
            self.db.add(profile)
            await self.db.flush()

        oauth_account = OAuthAccount(
            user_id=str(user.id),
            provider=OAuthProvider(oauth_data.provider.value),
            provider_user_id=oauth_data.provider_user_id,
            provider_email=oauth_data.email,
        )
        self.db.add(oauth_account)
        await self.db.flush()

        return user, oauth_account, is_new_user

    async def _get_oauth_account_by_provider_user_id(
        self, provider: "OAuthProviderEnum", provider_user_id: str
    ) -> OAuthAccount | None:
        """OAuth 계정 조회"""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == OAuthProvider(provider.value),
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> User | None:
        """ID로 사용자 조회"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
