"""
StrategyAgent Tool 스키마 정의
"""

from pydantic import BaseModel, Field

from schemas.eligibility_conditions import EligibilityConditions

"""
Tool 1: InterestCalculatorTool 스키마
역할: LLM 기반 이자 계산 도구
"""


class ProductInterestCalculation(BaseModel):
    """개별 상품 이자 계산 결과"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    interest: int = Field(description="사용자 예치기간 기준 세후 이자 (원)")
    calculation_detail: str = Field(description="계산 과정 상세 설명")
    applied_conditions: list[str] = Field(description="적용된 우대조건 목록")
    feasibility: str = Field(description="조건 달성 난이도 (높음/중간/낮음)")


class InterestCalculatorResult(BaseModel):
    """InterestCalculatorTool 결과"""

    calculations: list[ProductInterestCalculation] = Field(
        description="전체 상품별 이자 계산 결과"
    )
    total_products_calculated: int = Field(description="계산된 상품 수")
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    calculation_timestamp: str = Field(description="계산 수행 시간")
    highest_interest_products: list[str] = Field(
        description="수익률 상위 10개 상품명 목록"
    )
    success: bool = Field(description="계산 성공 여부")
    error: str | None = Field(default=None, description="에러 메시지")