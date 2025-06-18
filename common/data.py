import re

crwal_headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://new-m.pay.naver.com",
    "Accept": "application/json",
}

parking_list_base_url = "https://new-m.pay.naver.com/savings/api/v1/productList?productTypeCode=1001&regionCode=00&sortType=PRIME_INTEREST_RATE"
parking_detail_base_url = "https://new-m.pay.naver.com/savings/detail"

special_flag_keys = [
    "first_banking",
    "bank_app",
    "online",
    "using_salary_account",
    "using_utility_bill",
    "using_card",
]
# 첫거래, 은행앱사용, 비대면가입, 급여연동, 공과금연동, 카드사용


# 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
# 공통 불변 데이터
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "parking"
BASIC_COLLECTION_NAME = "products"
DETAIL_COLLECTION_NAME = "product_details"

# [기본 정보] 필드
BASIC_INFO_FIELD = {
    "product_name": "상품명",
    "product_code": "상품코드",
    "company_name": "은행명",
    "categories": "상품유형",
    "interest_rate": "기본금리",
    "prime_interest_rate": "우대금리",
}

# [상품 안내] 필드
PRODUCT_GUIDE_FIELD = {
    "amount_limit": "가입한도",  # HTML: 금액
    "signup_method": "가입방법",
    "target_customer": "대상고객",
}

# [금리 안내] 필드
INTEREST_GUIDE_FIELD = {
    "basic_rate_info": "기본금리정보",
    "preferential_details": "우대조건세부내용",
    "rate_type": "금리유형",
}

PRODUCT_FIELD = {
    # 기본 정보 (6개)
    **BASIC_INFO_FIELD,
    # [상품 안내] 필드
    "product_guide": PRODUCT_GUIDE_FIELD,
    # [금리 안내] 필드
    "interest_guide": INTEREST_GUIDE_FIELD,
}

# 카테고리 매핑 테이블
CATEGORY_FIELD = {
    "online": "방문없이가입",
    "anyone": "누구나가입",
    "specialOffer": "특판",
}


# 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
# 공통 함수
def camel_to_snake(camel_str):
    """
    camelCase 문자열을 snake_case로 변환합니다.

    Args:
        camel_str (str): camelCase 문자열

    Returns:
        str: snake_case 문자열
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_str).lower()


def snake_to_camel(snake_str):
    """
    snake_case 문자열을 camelCase로 변환합니다.

    Args:
        snake_str (str): snake_case 문자열

    Returns:
        str: camelCase 문자열
    """
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])
