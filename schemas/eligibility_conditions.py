"""
사용자 조건 스키마 정의
"""

from pydantic import BaseModel


class EligibilityConditions(BaseModel):
    """사용자 입력 조건"""

    min_interest_rate: float  # 최소 금리 기준

    # 카테고리 조건 리스트
    categories: list[str] = []  # ['online', 'anyone', 'specialOffer']

    # 우대조건 리스트
    special_conditions: list[str] = (
        []
    )  # ['first_banking', 'bank_app', 'online', 'using_salary_account', 'using_utility_bill', 'using_card']
