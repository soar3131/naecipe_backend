"""
취향 설정 관련 Enum 정의
SPEC-003: 사용자 프로필 및 취향 설정
"""
from enum import Enum


class DietaryRestriction(str, Enum):
    """식이 제한 유형"""
    VEGETARIAN = "vegetarian"       # 채식 (유제품/계란 허용)
    VEGAN = "vegan"                 # 비건 (동물성 제품 불가)
    PESCATARIAN = "pescatarian"     # 페스코 (해산물 허용)
    HALAL = "halal"                 # 할랄
    KOSHER = "kosher"               # 코셔
    GLUTEN_FREE = "gluten_free"     # 글루텐 프리
    LACTOSE_FREE = "lactose_free"   # 유당 불내증
    LOW_SODIUM = "low_sodium"       # 저염식
    LOW_SUGAR = "low_sugar"         # 저당식


class Allergy(str, Enum):
    """알레르기 유형"""
    PEANUT = "peanut"           # 땅콩
    TREE_NUT = "tree_nut"       # 견과류
    MILK = "milk"               # 우유
    EGG = "egg"                 # 달걀
    WHEAT = "wheat"             # 밀
    SOY = "soy"                 # 대두
    FISH = "fish"               # 생선
    SHELLFISH = "shellfish"     # 갑각류/조개류
    SESAME = "sesame"           # 참깨


class CuisineCategory(str, Enum):
    """요리 카테고리"""
    KOREAN = "korean"           # 한식
    JAPANESE = "japanese"       # 일식
    CHINESE = "chinese"         # 중식
    WESTERN = "western"         # 양식
    ITALIAN = "italian"         # 이탈리안
    MEXICAN = "mexican"         # 멕시칸
    THAI = "thai"               # 태국
    VIETNAMESE = "vietnamese"   # 베트남
    INDIAN = "indian"           # 인도
    FUSION = "fusion"           # 퓨전


# 프론트엔드 표시용 라벨 매핑
DIETARY_RESTRICTION_LABELS = {
    DietaryRestriction.VEGETARIAN: "채식 (유제품/계란 허용)",
    DietaryRestriction.VEGAN: "비건 (동물성 제품 불가)",
    DietaryRestriction.PESCATARIAN: "페스코 (해산물 허용)",
    DietaryRestriction.HALAL: "할랄",
    DietaryRestriction.KOSHER: "코셔",
    DietaryRestriction.GLUTEN_FREE: "글루텐 프리",
    DietaryRestriction.LACTOSE_FREE: "유당 불내증",
    DietaryRestriction.LOW_SODIUM: "저염식",
    DietaryRestriction.LOW_SUGAR: "저당식",
}

ALLERGY_LABELS = {
    Allergy.PEANUT: "땅콩",
    Allergy.TREE_NUT: "견과류",
    Allergy.MILK: "우유",
    Allergy.EGG: "달걀",
    Allergy.WHEAT: "밀",
    Allergy.SOY: "대두",
    Allergy.FISH: "생선",
    Allergy.SHELLFISH: "갑각류/조개류",
    Allergy.SESAME: "참깨",
}

CUISINE_CATEGORY_LABELS = {
    CuisineCategory.KOREAN: "한식",
    CuisineCategory.JAPANESE: "일식",
    CuisineCategory.CHINESE: "중식",
    CuisineCategory.WESTERN: "양식",
    CuisineCategory.ITALIAN: "이탈리안",
    CuisineCategory.MEXICAN: "멕시칸",
    CuisineCategory.THAI: "태국",
    CuisineCategory.VIETNAMESE: "베트남",
    CuisineCategory.INDIAN: "인도",
    CuisineCategory.FUSION: "퓨전",
}
