from typing import Literal

import pymongo
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime




class QuestionFilterToolsWrapper(BaseModel):
    """
    QuestionFilterAgent용 Tools Wrapper 스키마

    우대조건 질문 기반 2차 필터링을 위한 Tool들을 관리하는 딕셔너리 구조
    각 Tool은 특정 단계의 처리를 담당하며, 순차적으로 실행됨
    """

    condition_extractor: Any = Field(
        description="우대조건 및 금리정보 청크 데이터 추출 Tool"
    )
    pattern_analyzer: Any = Field(
        description="LLM 기반 우대조건 패턴 분석 및 RAG 쿼리 생성 Tool"
    )

"""
Tool 1: ConditionExtractorTool 스키마
역할: 우대조건 및 금리정보 청크 데이터 추출
"""


class ChunkData(BaseModel):
    """개별 청크 데이터"""

    chunk_type: str = Field(
        description="청크 타입 (basic_rate_info, preferential_details)"
    )
    chunk_index: int = Field(description="청크 인덱스 (2, 3)")
    content_natural: str = Field(description="자연어 청크 내용")


class ExtractedProduct(BaseModel):
    """우대조건 및 금리정보 데이터"""

    product_code: str = Field(description="상품 코드")
    product_name: str = Field(description="상품명")
    chunks: list[ChunkData] = Field(description="우대조건 및 금리정보 청크 목록")


class ConditionExtractorResult(BaseModel):
    """ConditionExtractorTool 결과"""

    products: list[ExtractedProduct] = Field(
        description="우대조건 및 금리정보 청크 데이터 목록"
    )
    total_products: int = Field(description="조회된 상품 수")
    total_chunks: int = Field(description="추출된 총 청크 수")
    success: bool = Field(description="추출 성공 여부")


"""
Tool 2: PatternAnalyzerTool 스키마
역할: LLM 기반 우대조건 패턴 분석 및 RAG 쿼리 생성
"""


class AnalysisPattern(BaseModel):
    """분석된 패턴 (금리정보 + 우대조건 통합)"""

    pattern_name: str = Field(
        description="패턴 이름 (예: 금리_기본금리, 우대_마케팅동의)"
    )
    pattern_type: str = Field(
        description="패턴 타입 (rate_info 또는 preferential_condition)"
    )
    frequency: int = Field(description="해당 패턴 빈도수")
    affected_banks: list[str] = Field(description="해당 패턴을 사용하는 은행 목록")
    standard_keyword: str = Field(description="표준화된 키워드")


class PatternAnalysisOutput(BaseModel):
    """LLM 출력 파싱용 스키마"""

    patterns: list[AnalysisPattern] = Field(description="분석된 패턴 목록")
    rag_queries: list[str] = Field(description="RAG 검색용 쿼리 목록")


class PatternAnalyzerResult(BaseModel):
    """PatternAnalyzerTool 결과"""

    analysis_patterns: list[AnalysisPattern] = Field(
        description="분석된 패턴 목록 (금리정보 + 우대조건)"
    )
    rag_queries: list[str] = Field(description="RAG 검색용 쿼리 목록")
    total_patterns: int = Field(description="총 패턴 수")
    analysis_success: bool = Field(description="분석 성공 여부")


"""
Tool 3: QuestionGeneratorTool 스키마
역할: 패턴 분석 결과 기반으로 RAG 검색하여 사용자 질문 생성
"""

class UserQuestion(BaseModel):
    """사용자에게 보여줄 개별 질문"""

    id: str = Field(
        description="질문 고유 ID (q1, q2, q3 형태)"
    )
    category: Literal[
        "online",  # 비대면가입
        "bank_app",  # 은행앱사용
        "using_salary_account",  # 급여연동
        "using_utility_bill",  # 공과금연동
        "using_card",  # 카드사용
        "first_banking"  # 첫거래
    ] = Field(
        description="우대조건 카테고리 (영문 코드)"
    )
    question: str = Field(
        description="사용자에게 보여줄 질문 텍스트 (Yes/No 답변 가능)"
    )
    impact: str = Field(
        description="해당 조건의 영향도나 중요성 설명"
    )


class QuestionGeneratorResult(BaseModel):
    """QuestionGeneratorTool 최종 결과"""

    questions: list[UserQuestion] = Field(
        description="생성된 사용자 질문 목록"
    )
    total_questions: int = Field(
        description="총 질문 수"
    )
    estimated_time: str = Field(
        description="예상 소요 시간 (예: '2-3분')"
    )
    generation_success: bool = Field(
        description="질문 생성 성공 여부"
    )

    class Config:
        """Pydantic 설정"""
        schema_extra = {
            "example": {
                "questions": [
                    {
                        "id": "q1",
                        "category": "은행앱사용",
                        "question": "해당 은행의 모바일 앱을 월 1회 이상 사용하실 수 있나요?",
                        "impact": "디지털 은행에서 주로 요구하는 조건입니다"
                    },
                    {
                        "id": "q2",
                        "category": "카드사용",
                        "question": "해당 은행의 체크카드나 신용카드로 월 30만원 이상 사용하고 계시나요?",
                        "impact": "기존 카드 사용 패턴 확인이 필요합니다"
                    }
                ],
                "total_questions": 2,
                "estimated_time": "2-3분",
                "generation_success": True
            }
        }


# 패턴명 → 카테고리 매핑 상수
PATTERN_TO_CATEGORY_MAP = {
    "우대_신규가입": "first_banking",
    "우대_앱사용": "bank_app",
    "우대_급여이체": "using_salary_account",
    "우대_자동이체": "using_utility_bill",
    "우대_카드실적": "using_card",
    "우대_마케팅동의": "online"  # 또는 적절한 영문명
}

"""
Tool 4: UserInputTool 스키마
역할: 환경별 적응형 사용자 입력 처리 (콘솔/API 자동 전환)
"""

class UserResponse(UserQuestion):
    """
    UserQuestion을 상속받은 사용자 응답 스키마
    질문 정보 + 사용자 답변 정보를 모두 포함
    """

    response_value: bool = Field(
        description="조건 충족 여부 (True/False)"
    )

    raw_response: str | None = Field(
        default=None,
        description="사용자 원본 응답 텍스트"
    )

    response_timestamp: datetime | None = Field(
        default=None,
        description="응답 시간"
    )


class UserInputResult(BaseModel):
    """
    Tool 4 (UserInputTool)의 최종 출력 스키마
    """

    user_responses: list[UserResponse] = Field(
        description="질문별 사용자 응답 목록"
    )

    response_summary: dict[str, bool] = Field(
        description=" 질문별 응답 요약"
    )

    total_questions: int = Field(description="총 질문 수")
    answered_questions: int = Field(description="답변된 질문 수")

    collection_success: bool = Field(description="응답 수집 성공 여부")

    class Config:
        """Pydantic 설정"""
        schema_extra = {
            "example": {
                "user_responses": [
                    {
                        "id": "q1",
                        "category": "bank_app",
                        "question": "해당 은행의 모바일 앱을 월 1회 이상 사용하실 수 있나요?",
                        "impact": "디지털 은행에서 주로 요구하는 조건입니다",
                        "response_value": True,
                        "raw_response": "네, 가능합니다"
                    }
                ],
                "response_summary": {
                    "bank_app": True,
                    "using_card": False
                },
                "total_questions": 3,
                "answered_questions": 3,
                "collection_success": True
            }
        }