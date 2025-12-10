"""
취향 설정 서비스 레이어
SPEC-003: 사용자 프로필 및 취향 설정
"""
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user_service.models.taste_preference import TastePreference
from user_service.models.user_profile import UserProfile
from user_service.schemas.enums import Allergy, CuisineCategory, DietaryRestriction
from user_service.schemas.preference import (
    PreferencesData,
    PreferencesUpdateRequest,
    TastePreferenceData,
    TasteValues,
)


class PreferenceService:
    """사용자 취향 설정 관리 서비스"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_preferences(self, user_id: str) -> Optional[PreferencesData]:
        """사용자 취향 설정 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            PreferencesData if found, None otherwise
        """
        # UserProfile 조회
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        # TastePreference 조회
        taste_result = await self.db.execute(
            select(TastePreference).where(TastePreference.user_id == user_id)
        )
        taste_prefs = taste_result.scalars().all()

        # 맛 취향을 딕셔너리로 변환
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
        data: PreferencesUpdateRequest,
    ) -> Optional[PreferencesData]:
        """사용자 취향 설정 수정

        Args:
            user_id: 사용자 UUID
            data: 수정할 취향 데이터

        Returns:
            Updated PreferencesData if found, None otherwise
        """
        # UserProfile 조회
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            return None

        # 제공된 필드만 업데이트 (partial update)
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

        # 맛 취향 업데이트
        if data.taste_preferences is not None:
            await self._update_taste_preferences(user_id, data.taste_preferences)

        await self.db.flush()
        await self.db.refresh(profile)

        # 업데이트된 데이터 반환
        return await self.get_preferences(user_id)

    async def _update_taste_preferences(
        self,
        user_id: str,
        taste_data: Dict[str, TasteValues],
    ) -> None:
        """맛 취향 업데이트

        Args:
            user_id: 사용자 UUID
            taste_data: 카테고리별 맛 취향 데이터
        """
        # 기존 취향 조회
        existing_result = await self.db.execute(
            select(TastePreference).where(TastePreference.user_id == user_id)
        )
        existing_prefs = {p.category: p for p in existing_result.scalars().all()}

        # overall 취향 먼저 처리 (다른 카테고리의 기본값)
        overall_values = taste_data.get("overall")

        for category, values in taste_data.items():
            if category in existing_prefs:
                # 기존 레코드 업데이트
                pref = existing_prefs[category]
                self._apply_taste_values(pref, values, overall_values, category != "overall")
            else:
                # 새 레코드 생성
                pref = TastePreference(
                    user_id=user_id,
                    category=category,
                )
                self._apply_taste_values(pref, values, overall_values, category != "overall")
                self.db.add(pref)

    def _apply_taste_values(
        self,
        pref: TastePreference,
        values: TasteValues,
        overall_values: Optional[TasteValues],
        inherit_overall: bool,
    ) -> None:
        """맛 취향 값 적용

        Args:
            pref: TastePreference 인스턴스
            values: 적용할 맛 취향 값
            overall_values: overall 취향 값 (상속용)
            inherit_overall: overall 값 상속 여부
        """
        # 값이 제공되면 적용, 없으면 overall 상속 또는 기존 값 유지
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

    async def get_dietary_options(self) -> List[Dict[str, str]]:
        """식이 제한 옵션 목록 조회"""
        from user_service.schemas.enums import DIETARY_RESTRICTION_LABELS
        return [
            {"value": d.value, "label": DIETARY_RESTRICTION_LABELS[d]}
            for d in DietaryRestriction
        ]

    async def get_allergy_options(self) -> List[Dict[str, str]]:
        """알레르기 옵션 목록 조회"""
        from user_service.schemas.enums import ALLERGY_LABELS
        return [
            {"value": a.value, "label": ALLERGY_LABELS[a]}
            for a in Allergy
        ]

    async def get_cuisine_options(self) -> List[Dict[str, str]]:
        """요리 카테고리 옵션 목록 조회"""
        from user_service.schemas.enums import CUISINE_CATEGORY_LABELS
        return [
            {"value": c.value, "label": CUISINE_CATEGORY_LABELS[c]}
            for c in CuisineCategory
        ]
