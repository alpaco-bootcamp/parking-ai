"""
사용자 조건 스키마 정의
"""

from pydantic import BaseModel, Field


class EligibilityConditions(BaseModel):
    """사용자 입력 조건"""

    min_interest_rate: float = Field(description="최소 금리 기준 (%)")
    categories: list[str] = Field(
        default=[],
        description="카테고리 조건 리스트 (예: 'online', 'anyone', 'specialOffer')"
    )
    special_conditions: list[str] = Field(
        default=[],
        description="우대조건 리스트 (예: 'first_banking', 'bank_app', 'online', 'using_salary_account', 'using_utility_bill', 'using_card')"
    )
    budget: int = Field(
        default=10000000,
        description="예치 금액 (원) / 기본: 1000만원"
    )
    deposit_period: int = Field(
        default=12,
        description="예치 가능 기간 (개월) / 기본: 12개월"
    )