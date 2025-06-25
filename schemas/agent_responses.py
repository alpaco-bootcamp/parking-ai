# schemas/agent_responses.py
from pydantic import BaseModel, Field
from typing import Optional, Any
from schemas.eligibility_conditions import EligibilityConditions


class FilterSummary(BaseModel):
    """필터링 결과 요약 정보"""
    total_analyzed: int = Field(description="분석 대상 상품 수")
    match_count: int = Field(description="조건 통과 상품 수")
    excluded_count: int = Field(description="조건 미달 상품 수")
    match_rate: float = Field(description="매칭률 (백분율)")
    execution_time: Optional[float] = Field(default=None, description="실행 시간 (초)")


class EligibilitySuccessResponse(BaseModel):
    """EligibilityAgent 성공 응답"""
    eligible_products: list[dict] = Field(description="필터링된 상품 목록")
    filter_summary: FilterSummary = Field(description="필터링 결과 요약")
    user_conditions: EligibilityConditions = Field(description="사용자 조건")
    processing_step: str = Field(default="eligibility_completed", description="처리 단계")
    next_agent: str = Field(default="FilterAgent", description="다음 에이전트")
    success: bool = Field(default=True, description="성공 여부")
    error: Optional[str] = Field(default=None, description="에러 메시지")


class EligibilityErrorResponse(BaseModel):
    """EligibilityAgent 에러 응답"""
    eligible_products: list[dict] = Field(default_factory=list, description="빈 상품 목록")
    filter_summary: FilterSummary = Field(
        default_factory=lambda: FilterSummary(
            total_analyzed=0,
            match_count=0,
            excluded_count=0,
            match_rate=0.0
        ),
        description="빈 필터링 결과"
    )
    user_conditions: Optional[EligibilityConditions] = Field(default=None, description="사용자 조건")
    processing_step: str = Field(default="eligibility_failed", description="처리 단계")
    next_agent: Optional[str] = Field(default=None, description="다음 에이전트")
    success: bool = Field(default=False, description="성공 여부")
    error: str = Field(description="에러 메시지")