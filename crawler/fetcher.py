import math

import requests
from common.data import parking_list_base_url


def fetch_parking_list():

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://new-m.pay.naver.com",
        "Accept": "application/json",
    }

    response = requests.get(parking_list_base_url, headers=headers)
    data = response.json()  # Dict
    result = data.get("result")
    total_count, size = result.get("totalCount"), result.get("size")
    call_num = math.ceil(int(total_count) / int(size))

    total_product_list = []

    for i in range(call_num):
        url = f"{parking_list_base_url}&offset={i * 20}"
        response = requests.get(url, headers=headers)
        data = response.json()  # Dict
        result = data.get("result")

        product_list = [
            {
                "product_name": product.get("name"), # 상품 이름
                "product_code": product.get("code"), # 상품 코드
                "company_name": product.get("companyName"), # 은행 이름
                "company_code": product.get("companyCode"), # 은행 코드
                "interest_rate": product.get("interestRate"), # 기본 금리
                "primeInterest_rate": product.get("primeInterestRate"), # 우대 금리
                "categories": product.get("productCategories"), # 카테고리 (방문없이 가입, 누구나 가입, 특판)

            } for product in result.get("products")
        ]
        total_product_list.extend(product_list)

    # 최종 데이터
    print('total_product_list', len(total_product_list), total_product_list[0])


def fetch():
    # 파킹통장 상품 리스트 크롤링
    fetch_parking_list()
    # 각 파킹통장 detail


if __name__ == "__main__":
    fetch()
