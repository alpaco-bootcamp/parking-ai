"""
StrategyAgent Tool 스키마 정의
"""
from enum import Enum
from pydantic import BaseModel, Field

from schemas.eligibility_conditions import EligibilityConditions
from schemas.question_tool_schema import UserResponse
from typing import Any

"""
Tool 1: InterestCalculatorTool 스키마
역할: LLM 기반 이자 계산 도구
"""


class StrategyToolsWrapper(BaseModel):
    """
    StrategyAgent용 Tools Wrapper 스키마

    전략 수립 및 이자 계산을 위한 Tool들을 관리하는 딕셔너리 구조
    각 Tool은 특정 단계의 처리를 담당하며, 순차적으로 실행됨
    """

    interest_calculator: Any = Field(
        description="LLM 기반 파킹통장 이자 계산 Tool"
    )
    strategy_scenario: Any = Field(
        description="3가지 전략 시나리오 생성 Tool"
    )


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
    interest: int = Field(
        description="사용자 예치기간 기준 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 152594"
    )
    calculation_detail: str = Field(description="계산 과정 상세 설명")
    applied_conditions: list[str] = Field(description="적용된 우대조건 목록")


class InterestCalculationOutput(BaseModel):
    """이자계산 LLM 출력 파싱용 스키마"""

    calculations: list[ProductInterestCalculation] = Field(description="계산 결과 목록")

class InterestCalculatorResult(BaseModel):
    """InterestCalculatorTool 결과"""

    calculations: list[ProductInterestCalculation] = Field(
        description="전체 상품별 이자 계산 결과"
    )
    user_responses: list[UserResponse] = Field(description="사용자 질문-답변 목록")
    total_products_calculated: int = Field(
        description="계산된 상품 수. 콤마 없는 순수 정수로 출력 필수. 예: 15"
    )
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    calculation_timestamp: str = Field(description="계산 수행 시간")
    success: bool = Field(description="계산 성공 여부")
    error: str | None = Field(default=None, description="에러 메시지")


"""
Tool 2: StrategyScenarioTool 스키마
역할: 3가지 전략 시나리오 수립 (단일형/분산형/고수익형)
"""


class ScenarioTypeEnum(str, Enum):
    """시나리오 타입 열거형"""
    SINGLE = "single"  # 단일형
    DISTRIBUTED = "distributed"  # 분산형
    HIGH_YIELD = "high_yield"  # 고수익형


class ProductAllocation(BaseModel):
    """개별 상품별 예치 배분"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    allocated_amount: int = Field(
        description="배분 예치 금액 (원). 콤마 없는 순수 정수로 출력 필수."
    )
    interest_rate: float = Field(description="적용 금리 (%)")
    deposit_period_months: int = Field(description="예치 기간 (개월)")
    conditions_required: list[str] = Field(
        default_factory=list,
        description="필요한 우대조건 목록"
    )
    expected_interest_6m: int = Field(
        description="6개월 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 76297"
    )
    expected_interest_1y: int = Field(
        description="1년 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 152594"
    )
    expected_interest_3y: int = Field(
        description="3년 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 457782"
    )


class ScenarioDetails(BaseModel):
    """개별 시나리오 상세 정보"""

    scenario_type: ScenarioTypeEnum = Field(description="시나리오 타입")
    scenario_name: str = Field(description="시나리오명 (예: '단일통장 집중형/분산형 통장 쪼개기/수익률 최우선 전략')")
    scenario_content: str = Field(description="완성된 시나리오 상세 내용 (사용자 출력용)")
    products: list[ProductAllocation] = Field(description="상품별 배분 목록")
    total_allocated_amount: int = Field(
        description="총 배분 금액 (원). 콤마 없는 순수 정수로 출력 필수. 예: 20000000"
    )

    # 총 예상 수익
    total_expected_interest_6m: int = Field(
        description="6개월 총 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 152594"
    )
    total_expected_interest_1y: int = Field(
        description="1년 총 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 305188"
    )
    total_expected_interest_3y: int = Field(
        description="3년 총 예상 세후 이자 (원). 콤마 없는 순수 정수로 출력 필수. 예: 915564"
    )

    # 시나리오 특징
    scenario_summary: str = Field(description="시나리오 요약 및 특징")
    advantages: list[str] = Field(description="장점 목록")
    disadvantages: list[str] = Field(description="단점 목록")
    recommended_for: str = Field(description="추천 대상 (어떤 사용자에게 적합한지)")
    condition_achievement_rate: float = Field(
        description="우대조건 달성률 (0.0~1.0)"
    )


class StrategyScenarioOutput(BaseModel):
    """LLM 출력 파싱용 스키마"""

    scenarios: list[ScenarioDetails] = Field(
        description="3가지 시나리오 목록"
    )

class StrategyScenarioResult(BaseModel):
    """StrategyScenarioTool 최종 결과"""

    scenarios: list[ScenarioDetails] = Field(
        description="설계된 3가지 시나리오 목록"
    )
    interest_calculations: list[ProductInterestCalculation] = Field(  # 추가
        description="상품별 이자 계산 결과"
    )
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    user_responses: list[UserResponse] = Field(
        description="사용자 질문-답변 목록"
    )

    # 실행 결과
    generation_success: bool = Field(description="시나리오 생성 성공 여부")
    error: str | None = Field(default=None, description="에러 메시지")

