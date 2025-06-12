import math

import requests
from bs4 import BeautifulSoup

from common.data import parking_list_base_url, BASIC_COLLECTION_NAME, crwal_headers, special_flag_keys, camel_to_snake, \
    snake_to_camel, parking_detail_base_url
from crawler.save_db import insert_document, drop_collection, get_all_documents


def process_special_conditons(product_list: list[dict]) -> list[dict]:
    """
    상품 데이터에 우대조건을 적용합니다.

    각 우대조건별로 API를 호출하여 해당 조건을 만족하는 상품들을 찾고,
    입력받은 데이터에서 매칭되는 상품의 우대조건을 True로 업데이트합니다.

    Args:
        product_list (List[Dict]): 우대조건을 적용할 상품 데이터 리스트
        각 딕셔너리는 'code'와 'special_conditions' 키를 포함해야 함

    Returns:
        List[Dict]: 우대조건이 적용된 상품 데이터 리스트
    """
    for flag_key in special_flag_keys:
        # 상품 인덱스 생성 (성능 최적화)
        products_index = { product['code']: i for i, product in enumerate(product_list)}
        update_count = 0

        url = f'{parking_list_base_url}&specialConditions%5B%5D={snake_to_camel(flag_key)}'
        response = requests.get(url, headers=crwal_headers)
        result = response.json()  # Dict
        result_data = result.get('result')
        total_count, size = result_data.get("totalCount"), result_data.get("size")

        if total_count == 0:
            print(f"⚠️ '{flag_key}' 조건에 해당하는 상품이 없습니다.")
            continue

        call_num = math.ceil(int(total_count) / int(size))

        # 페이징처리
        for i in range(call_num):
            url = f'{parking_list_base_url}&specialConditions%5B%5D={snake_to_camel(flag_key)}&offset={i * 20}'
            response = requests.get(url, headers=crwal_headers)
            result = response.json()  # Dict

            products = result.get('result', {}).get('products', [])
            eligible_codes = [product.get('code') for product in products]

            for code in eligible_codes:
                if code in products_index:
                    idx = products_index[code]
                    product_list[idx]['special_conditions'].update({flag_key: True})
                    update_count += 1

        print(f'{flag_key}: {update_count}개 업데이트!')

    return product_list


def fetch_parking_list() -> list[dict]:
    """
    네이버 금융 API에서 파킹통장 상품 목록을 크롤링하여 전체 상품 정보를 리스트로 반환합니다.

    요청 결과를 페이지 단위로 나누어 모두 순회하며, 각 상품의 기본 정보를 정제된 딕셔너리 형태로 수집합니다.

    Returns:
        List[Dict]: 파킹통장 상품 정보가 담긴 리스트.
                    각 항목은 다음과 같은 필드를 포함합니다:
                    - product_name (str): 상품 이름
                    - product_code (str): 상품 코드
                    - company_name (str): 금융사 이름
                    - company_code (str): 금융사 코드
                    - interest_rate (str): 기본 금리
                    - primeInterest_rate (str): 우대 금리
                    - categories (List[str]): 상품 카테고리 목록 (예: online, anyone, special)
    """


    response = requests.get(parking_list_base_url, headers=crwal_headers)
    data = response.json()  # Dict
    result = data.get("result")
    total_count, size = result.get("totalCount"), result.get("size")
    call_num = math.ceil(int(total_count) / int(size))

    total_product_list = []

    for i in range(call_num):
        url = f"{parking_list_base_url}&offset={i * 20}"
        response = requests.get(url, headers=crwal_headers)
        data = response.json()  # Dict
        result = data.get("result")

        product_list = [
            {
                "product_name": product.get("name"),  # 상품 이름
                "product_code": product.get("code"),  # 상품 코드
                "company_name": product.get("companyName"),  # 은행 이름
                "company_code": product.get("companyCode"),  # 은행 코드
                "interest_rate": float(product.get("interestRate")),  # 기본 금리
                "prime_interest_rate": float(
                    product.get("primeInterestRate")
                ),  # 우대 금리
                "categories": product.get(
                    "productCategories"
                ),  # 카테고리 (방문없이 가입, 누구나 가입, 특판)
                "special_conditions": { # 우대조건
                    key : False  for key in special_flag_keys
                }

            }
            for product in result.get("products")
        ]
        total_product_list.extend(product_list)

    # 우대조건 전처리 데이터
    processed_product_list = process_special_conditons(total_product_list)

    # 최종 데이터
    return processed_product_list


def fetch_parking_detail():
    product_list = list(get_all_documents(BASIC_COLLECTION_NAME))


    for i, product in enumerate(product_list):
        if i > 3:
            break
        response = requests.get(f'{parking_detail_base_url}/{product["code"]}')
        print(f"response.content: {response.content}")

        soup = BeautifulSoup(response.content, 'lxml')



    print('끝')


def fetch():
    # 파킹통장 상품 리스트 크롤링
    # product_list = fetch_parking_list()

    # 크롤링한 데이터 저장
    # insert_document(data=product_list, collection_name=BASIC_COLLECTION_NAME)

    # drop_collection(BASIC_COLLECTION_NAME)

    # 각 파킹통장 detail
    fetch_parking_detail()


if __name__ == "__main__":
    fetch()
