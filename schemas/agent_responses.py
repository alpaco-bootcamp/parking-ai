# schemas/agent_responses.py
from pydantic import BaseModel, Field
from typing import Optional
from schemas.eligibility_conditions import EligibilityConditions
from schemas.question_tool_schema import UserResponse
from schemas.strategy_tool_schema import ScenarioDetails, ProductInterestCalculation


class SimpleProduct(BaseModel):
    """간단한 상품 정보"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")


class FilterSummary(BaseModel):
    """필터링 결과 요약 정보"""

    total_analyzed: int = Field(description="분석 대상 상품 수")
    match_count: int = Field(description="조건 통과 상품 수")
    excluded_count: int = Field(description="조건 미달 상품 수")
    match_rate: float = Field(description="매칭률 (백분율)")
    execution_time: Optional[float] = Field(default=None, description="실행 시간 (초)")


# EligibilityAgent 응답


class EligibilitySuccessResponse(BaseModel):
    """EligibilityAgent 성공 응답"""

    result_products: list[SimpleProduct] = Field(description="필터링된 상품 목록")
    filter_summary: FilterSummary = Field(description="필터링 결과 요약")
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    processing_step: str = Field(
        default="eligibility_completed", description="처리 단계"
    )
    next_agent: str = Field(default="FilterQuestionAgent", description="다음 에이전트")
    success: bool = Field(default=True, description="성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class EligibilityErrorResponse(BaseModel):
    """EligibilityAgent 에러 응답"""

    result_products: list[dict] = Field(
        default_factory=list, description="빈 상품 목록"
    )
    filter_summary: FilterSummary = Field(
        default_factory=lambda: FilterSummary(
            total_analyzed=0, match_count=0, excluded_count=0, match_rate=0.0
        ),
        description="빈 필터링 결과",
    )
    user_conditions: Optional[EligibilityConditions] = Field(
        default=None, description="사용자 조건"
    )
    processing_step: str = Field(default="eligibility_failed", description="처리 단계")
    next_agent: Optional[str] = Field(default=None, description="다음 에이전트")
    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(description="에러 메시지")


# QuestionAgent 응답
class QuestionSuccessResponse(BaseModel):
    """QuestionAgent 성공 응답"""

    eligible_products: list[SimpleProduct] = Field(description="1차 필터링된 통장 목록")
    user_responses: list[UserResponse] = Field(
        description="사용자 질문-답변 목록"
    )  # 추가
    response_summary: dict[str, bool] = Field(
        description="질문별 조건 충족 여부 요약"
    )  # 추가
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    processing_step: str = Field(default="question_completed", description="처리 단계")
    next_agent: str = Field(default="StrategyAgent", description="다음 에이전트")
    success: bool = Field(default=True, description="성공 여부")
    error: str | None = Field(
        default=None, description="에러 메시지"
    )  # Optional → str | None


class QuestionErrorResponse(BaseModel):
    """QuestionAgent 에러 응답"""

    eligible_products: list[SimpleProduct] = Field(
        default_factory=list, description="빈 상품 목록"
    )
    user_responses: list[UserResponse] = Field(  # 추가
        default_factory=list, description="빈 응답 목록"
    )
    response_summary: dict[str, bool] = Field(  # 추가
        default_factory=dict, description="빈 응답 요약"
    )
    user_conditions: EligibilityConditions | None = Field(  # Optional → | None
        default=None, description="사용자 조건"
    )
    processing_step: str = Field(default="question_failed", description="처리 단계")
    next_agent: str | None = Field(
        default=None, description="다음 에이전트"
    )  # Optional → str | None
    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(description="에러 메시지")


class StrategySuccessResponse(BaseModel):
    """StrategyAgent 성공 응답"""

    scenarios: list[ScenarioDetails] = Field(
        description="설계된 3가지 시나리오 목록 (단일형/분산형/고수익형)"
    )
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    user_responses: list[UserResponse] = Field(
        description="사용자 질문-답변 목록"
    )
    response_summary: dict[str, bool] = Field(
        description="질문별 조건 충족 여부 요약"
    )
    interest_calculations: list[ProductInterestCalculation] = Field(
        description="상품별 이자 계산 결과"
    )
    processing_step: str = Field(default="strategy_completed", description="처리 단계")
    next_agent: str = Field(default="ComparatorAgent", description="다음 에이전트")
    success: bool = Field(default=True, description="성공 여부")
    error: str | None = Field(default=None, description="에러 메시지")


class StrategyErrorResponse(BaseModel):
    """StrategyAgent 에러 응답"""

    scenarios: list[ScenarioDetails] = Field(
        default_factory=list, description="빈 시나리오 목록"
    )
    user_conditions: EligibilityConditions | None = Field(
        default=None, description="사용자 조건"
    )
    user_responses: list[UserResponse] = Field(
        default_factory=list, description="빈 응답 목록"
    )
    response_summary: dict[str, bool] = Field(
        default_factory=dict, description="빈 응답 요약"
    )
    interest_calculations: list[ProductInterestCalculation] = Field(
        default_factory=list, description="빈 계산 결과 목록"
    )
    processing_step: str = Field(default="strategy_failed", description="처리 단계")
    next_agent: str | None = Field(default=None, description="다음 에이전트")
    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(description="에러 메시지")