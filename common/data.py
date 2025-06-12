import re

crwal_headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://new-m.pay.naver.com",
    "Accept": "application/json",
}

parking_list_base_url = "https://new-m.pay.naver.com/savings/api/v1/productList?productTypeCode=1001&regionCode=00&sortType=PRIME_INTEREST_RATE"
parking_detail_base_url = "https://new-m.pay.naver.com/savings/detail/"

special_flag_keys = ['first_banking', 'bank_app', 'online', 'using_salary_account', 'using_utility_bill', 'using_card']
                     # 첫거래, 은행앱사용, 비대면가입, 급여연동, 공과금연동, 카드사용


# 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
# 공통 불변 데이터

DB_NAME = "parking"
BASIC_COLLECTION_NAME = "products"


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
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()


def snake_to_camel(snake_str):
    """
    snake_case 문자열을 camelCase로 변환합니다.

    Args:
        snake_str (str): snake_case 문자열

    Returns:
        str: camelCase 문자열
    """
    components = snake_str.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])