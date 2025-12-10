"""Pydantic schemas for User Service"""

from user_service.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from user_service.schemas.enums import (
    Allergy,
    CuisineCategory,
    DietaryRestriction,
    ALLERGY_LABELS,
    CUISINE_CATEGORY_LABELS,
    DIETARY_RESTRICTION_LABELS,
)
from user_service.schemas.preference import (
    OptionItem,
    OptionsResponse,
    PreferencesData,
    PreferencesResponse,
    PreferencesUpdateRequest,
    TastePreferenceData,
    TasteValues,
)
from user_service.schemas.profile import (
    ProfileData,
    ProfileResponse,
    ProfileUpdateRequest,
)
from user_service.schemas.user import RegisterResponse, UserInDB, UserResponse

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    # User
    "RegisterResponse",
    "UserResponse",
    "UserInDB",
    # Enums
    "Allergy",
    "CuisineCategory",
    "DietaryRestriction",
    "ALLERGY_LABELS",
    "CUISINE_CATEGORY_LABELS",
    "DIETARY_RESTRICTION_LABELS",
    # Profile
    "ProfileData",
    "ProfileResponse",
    "ProfileUpdateRequest",
    # Preferences
    "OptionItem",
    "OptionsResponse",
    "PreferencesData",
    "PreferencesResponse",
    "PreferencesUpdateRequest",
    "TastePreferenceData",
    "TasteValues",
]
