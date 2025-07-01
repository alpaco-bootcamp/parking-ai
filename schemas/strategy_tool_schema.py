"""
StrategyAgent Tool 스키마 정의
"""

from pydantic import BaseModel, Field

from schemas.eligibility_conditions import EligibilityConditions

"""
Tool 1: InterestCalculatorTool 스키마
역할: LLM 기반 이자 계산 도구
"""



class ChunkInfo(BaseModel):
    """청크 정보"""

    chunk_type: str = Field(description="청크 타입 (basic_rate_info, preferential_details)")
    content_natural: str = Field(description="자연어 청크 내용")


class ProductDetailInfo(BaseModel):
    """상품 상세 정보 (MongoDB 조회 결과)"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    chunks: list[ChunkInfo] = Field(description="금리정보 및 우대조건 청크 목록")

class ProductInterestCalculation(BaseModel):
    """개별 상품 이자 계산 결과"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    interest: int = Field(description="사용자 예치기간 기준 세후 이자 (원)")
    calculation_detail: str = Field(description="계산 과정 상세 설명")
    applied_conditions: list[str] = Field(description="적용된 우대조건 목록")
    feasibility: str = Field(description="조건 달성 난이도 (높음/중간/낮음)")


class InterestCalculationOutput(BaseModel):
    """이자계산 LLM 출력 파싱용 스키마"""

    calculations: list[ProductInterestCalculation] = Field(description="계산 결과 목록")

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