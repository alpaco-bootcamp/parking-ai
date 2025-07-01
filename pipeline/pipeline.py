from typing import Any
from langchain.schema.runnable import RunnableSequence, Runnable
from langchain_core.language_models import BaseLanguageModel

from agents.eligibility_agent import EligibilityAgent
from agents.question_agent import QuestionAgent
from schemas.eligibility_conditions import EligibilityConditions
from schemas.agent_responses import (
    EligibilitySuccessResponse,
    EligibilityErrorResponse,
    QuestionErrorResponse,
    QuestionSuccessResponse,
)
from schemas.question_tool_schema import UserInputResult


class Pipeline:
    """
    파킹통장 추천 멀티에이전트 파이프라인

    현재는 EligibilityAgent만 구현되어 있으며, 향후 FilterQuestionAgent, StrategyAgent 등이 추가될 예정
    """

    def __init__(self, llm: BaseLanguageModel, test_mode: bool = True) -> None:
        """
        파이프라인 초기화

         Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
            test_mode: 테스트 모드 여부 (콘솔/API 전환용)

        """

        # 에이전트 초기화
        self.eligibility_agent = EligibilityAgent()  # rule_base기반
        self.question_agent = QuestionAgent(llm, test_mode)
        # TODO: 향후 추가될 에이전트들
        # self.strategy_agent = StrategyAgent()
        # self.comparator_agent = ComparatorAgent()
        # self.formatter_agent = FormatterAgent()

        # 현재 파이프라인 구성
        # self.pipeline = self.build_pipeline_single() # 단일
        self.pipeline = self.build_pipeline()  # 다중

        print("✅ MultiAgentPipeline 초기화 완료")

    def build_pipeline_single(self) -> Runnable:
        """
        에이전트 단일 파이프라인 구성

        Returns:
            Runnable: 구성된 파이프라인
        """
        # 현재는 EligibilityAgent만 있으므로 단일 Runnable 반환
        return self.eligibility_agent.runnable

    def build_pipeline(self) -> RunnableSequence:
        """
        에이전트 파이프라인 구성

        Returns:
            RunnableSequence: 구성된 파이프라인
        """
        # 각 단계의 출력이 다음 단계의 입력이 됨
        pipeline_components = [
            self.eligibility_agent.runnable,
            self.question_agent.runnable,  # 역질문
            # TODO: 향후 추가될 에이전트들
            # self.strategy_agent.runnable,
            # self.comparator_agent.runnable,
            # self.formatter_agent.runnable
        ]

        return RunnableSequence(*pipeline_components)

    def run(
        self, conditions: EligibilityConditions
    ) -> QuestionSuccessResponse | QuestionErrorResponse:
        """
        파이프라인 실행

        Args:
            conditions: 사용자 우대조건

        Returns:
            QuestionSuccessResponse | QuestionErrorResponse: 사용자 질문-답변 데이터 + 적격 통장 목록
        """
        print("🚀 MultiAgentPipeline 실행 시작")

        try:
            # 입력 데이터 구성
            input_data = {"conditions": conditions}

            print(f"   📝 입력 조건: {input_data.get('conditions', {})}")

            # 파이프라인 실행
            result = self.pipeline.invoke(input_data)

            print("🎯 MultiAgentPipeline 실행 완료")
            return result

        except Exception as e:
            print(f"❌ MultiAgentPipeline 실행 오류: {e}")
            return QuestionErrorResponse(error=f"파이프라인 실행 실패: {str(e)}")

    @staticmethod
    def get_pipeline_info() -> dict[str, Any]:
        """
        파이프라인 정보 반환

        Returns:
            dict: 파이프라인 구성 정보
        """
        return {
            "total_agents": 1,  # 현재는 EligibilityAgent만
            "current_agents": ["EligibilityAgent"],
            "planned_agents": [
                "FilterQuestionAgent",
                "StrategyAgent",
                "ComparatorAgent",
                "FormatterAgent",
            ],
            "pipeline_status": "partial_implementation",
        }
