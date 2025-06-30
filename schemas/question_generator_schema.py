from pydantic import BaseModel, Field
from typing import Literal


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