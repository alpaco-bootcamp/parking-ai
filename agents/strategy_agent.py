import time
from langchain.schema.runnable import RunnableLambda, RunnableSequence
from langchain_core.language_models import BaseLanguageModel

from schemas.strategy_tool_schema import StrategyScenarioResult, InterestCalculatorResult
from tools.wrappers.strategy_tool_wrappers import StrategyTools
from schemas.agent_responses import (
    QuestionSuccessResponse,
    StrategySuccessResponse,
    StrategyErrorResponse,
)


class StrategyAgent:
    """
    3가지 전략 시나리오 수립 및 이자 계산 에이전트

    처리 단계:
    1. InterestCalculatorTool: LLM 기반 상품별 이자 계산
    2. StrategyScenarioTool: 3가지 전략 시나리오 생성 (단일형/분산형/고수익형)
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Agent 초기화

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
        """
        self.llm = llm

        # Tools 초기화
        self.tools = StrategyTools.get_tools(llm)

        # Runnable 객체로 반환하여 파이프라인에서 실행
        self.runnable = RunnableLambda(self.execute)

        print("✅ StrategyAgent 초기화 완료")

    def _build_runnable_chain(self) -> RunnableSequence:
        """
        RunnableSequence 체인 구성

        Returns:
            RunnableSequence: Tool들이 직접 연결된 Runnable 체인
        """
        return RunnableSequence(
            # QuestionSuccessResponse → InterestCalculatorResult
            self.tools.interest_calculator,  # Step 1: InterestCalculator Tool 실행
            # InterestCalculatorResult → StrategyScenarioResult
            self.tools.strategy_scenario,  # Step 2: StrategyScenario Tool 실행
        )

    @staticmethod
    def _format_success_response(
        scenario_result: StrategyScenarioResult,
    ) -> StrategySuccessResponse:
        """
        성공적인 실행 결과를 표준 응답 포맷으로 변환

        Args:
            scenario_result: StrategyScenarioResult - 시나리오 생성 결과

        Returns:
            StrategySuccessResponse: 표준화된 성공 응답
        """
        return StrategySuccessResponse(
            scenarios=scenario_result.scenarios,
            user_conditions=scenario_result.user_conditions,
            user_responses=scenario_result.user_responses,
            response_summary={
                response.id: response.response_value
                for response in scenario_result.user_responses
            },
            interest_calculations=scenario_result.interest_calculations,
            processing_step="strategy_completed",
            next_agent="ComparatorAgent",
            success=True,
            error=None
        )

    @staticmethod
    def _format_error_response(error_message: str) -> StrategyErrorResponse:
        """
        에러 발생 시 표준 응답 포맷으로 변환

        Args:
            error_message: 에러 메시지

        Returns:
            StrategyErrorResponse: 표준화된 에러 응답
        """
        return StrategyErrorResponse(error=error_message)

    def execute(
        self, question_response: QuestionSuccessResponse
    ) -> StrategySuccessResponse | StrategyErrorResponse:
        """
        Agent 실행

        Args:
            question_response: QuestionAgent의 출력 결과

        Returns:
            StrategySuccessResponse | StrategyErrorResponse: 전략 시나리오 데이터
        """
        start_time = time.time()
        print("🚀 StrategyAgent 실행 시작")

        try:
            # 입력 데이터 검증
            if not question_response.success:
                raise ValueError("QuestionAgent 실행이 실패한 상태입니다.")

            if not question_response.eligible_products:
                raise ValueError("적격 상품이 없습니다.")

            if not question_response.user_responses:
                raise ValueError("사용자 응답이 없습니다.")

            print(
                f"✅ 입력 검증 완료: {len(question_response.eligible_products)}개 상품, "
                f"{len(question_response.user_responses)}개 사용자 응답"
            )

            # Tool 체인 실행
            tool_chain = self._build_runnable_chain()
            scenario_result = tool_chain.invoke(question_response)

            # 성공 검증
            if not scenario_result.generation_success:
                raise ValueError(f"시나리오 생성 실패: {scenario_result.error}")

            if not scenario_result.scenarios or len(scenario_result.scenarios) != 3:
                raise ValueError(f"시나리오 개수 오류: {len(scenario_result.scenarios)}개 (3개 필요)")

            execution_time = time.time() - start_time
            print(f"✅ StrategyAgent 실행 완료 (소요시간: {execution_time:.2f}초)")

            # 최종 정보 출력
            print(f"📊 생성된 시나리오: {len(scenario_result.scenarios)}개")
            for i, scenario in enumerate(scenario_result.scenarios, 1):
                print(f"  - 시나리오 정보 {i}: {scenario.scenario_name} ({scenario.scenario_type})")
                print(f"  🔥 시나리오 스크립트 \n {scenario.scenario_content} ")

            return self._format_success_response(scenario_result)

        except Exception as e:
            error_msg = f"StrategyAgent RunnableSequence 실행 오류: {str(e)}"
            print(f"❌ {error_msg}")
            return self._format_error_response(error_msg)