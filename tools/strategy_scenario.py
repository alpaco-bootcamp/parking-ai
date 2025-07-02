"""
StrategyScenarioTool
역할: LLM 기반 파킹통장 전략 시나리오 생성 도구
"""

from langchain.schema.runnable import Runnable
from langchain_core.language_models import BaseLanguageModel

from schemas.strategy_tool_schema import (
    InterestCalculatorResult,
    StrategyScenarioResult,
    StrategyScenarioOutput,
    ScenarioDetails, ProductInterestCalculation,
)
from schemas.eligibility_conditions import EligibilityConditions
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda

from prompts.strategy_prompts import StrategyPrompts


class StrategyScenarioTool(Runnable):
    """
    LLM 기반 파킹통장 전략 시나리오 생성 Tool

    입력: InterestCalculatorResult
    출력: StrategyScenarioResult
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Tool 초기화

        Args:
            llm: 사용할 llm모델
        """
        super().__init__()
        self.llm = llm

        # OutputParser 초기화
        self.output_parser = PydanticOutputParser(pydantic_object=StrategyScenarioOutput)

        print("✅ StrategyScenarioTool 초기화 완료")

    @staticmethod
    def _get_top_calculations(calculations: list[ProductInterestCalculation], top_n: int = 10) -> list[
        ProductInterestCalculation]:
        """
        이자 금액 기준 상위 N개 계산 결과 추출

        Args:
            calculations: 전체 이자 계산 결과
            top_n: 추출할 상위 개수

        Returns:
            list[ProductInterestCalculation]: 상위 N개 계산 결과
        """
        try:
            sorted_calculations = sorted(
                calculations,
                key=lambda x: x.interest,
                reverse=True
            )
            return sorted_calculations[:top_n]

        except Exception as e:
            print(f"❌ 상위 계산 결과 추출 실패: {str(e)}")
            return calculations[:top_n] if len(calculations) >= top_n else calculations

    def generate_scenarios_with_llm(self, interest_result: InterestCalculatorResult) -> list[ScenarioDetails]:
        """
        LLM을 사용하여 3가지 전략 시나리오 생성

        Args:
            interest_result: 이자 계산 결과

        Returns:
            list[ScenarioDetails]: 생성된 시나리오 목록
        """
        try:
            print("🔄 LLM 기반 시나리오 생성 중...")

            # 1. 상위 10개 계산 결과만 추출
            top_calculations = self._get_top_calculations(interest_result.calculations)

            # 2. 프롬프트 생성 (user_responses도 함께 전달)
            prompts = StrategyPrompts()
            prompt_text = prompts.create_strategy_scenario_prompt(
                top_interest_calculations=top_calculations,
                user_conditions=interest_result.user_conditions,
                user_responses=interest_result.user_responses,
                max_account_number=5
            )

            # 3. 프롬프트 템플릿 설정
            prompt_template = PromptTemplate(
                template=prompt_text + "\n\n{format_instructions}",
                input_variables=[],
                partial_variables={
                    "format_instructions": self.output_parser.get_format_instructions()
                },
            )

            print("🤖 LLM 시나리오 생성 중...")

            # 4. LCEL 체이닝 구성
            chain = (
                    RunnablePassthrough()
                    | prompt_template
                    | self.llm
                    | self.output_parser
                    | RunnableLambda(self._convert_scenario_to_schema)
            )

            # 4. 체인 실행
            scenarios = chain.invoke({})

            if scenarios and len(scenarios) == 3:
                print(f"✅ 시나리오 생성 완료: {len(scenarios)}개")
                return scenarios
            else:
                print(f"⚠️ 시나리오 생성 부분 실패: {len(scenarios) if scenarios else 0}개")
                return scenarios if scenarios else []

        except Exception as e:
            print(f"❌ LLM 시나리오 생성 실패: {str(e)}")
            return []

    @staticmethod
    def _convert_scenario_to_schema(llm_output: StrategyScenarioOutput) -> list[ScenarioDetails]:
        """
        LLM 파싱된 출력을 최종 결과 스키마로 변환

        Args:
            llm_output: Pydantic OutputParser로 파싱된 LLM 출력

        Returns:
            list[ScenarioDetails]: 최종 시나리오 결과
        """
        try:
            return llm_output.scenarios

        except Exception as e:
            print(f"❌ 시나리오 결과 스키마 변환 실패: {str(e)}")
            return []

    @staticmethod
    def _format_success_response(
            scenarios: list[ScenarioDetails],
            interest_result: InterestCalculatorResult
    ) -> StrategyScenarioResult:
        """
        성공적인 시나리오 생성 결과 포맷팅

        Args:
            scenarios: 생성된 시나리오 목록
            interest_result: 원본 이자 계산 결과

        Returns:
            StrategyScenarioResult: 성공 응답
        """
        return StrategyScenarioResult(
            scenarios=scenarios,
            user_conditions=interest_result.user_conditions,
            user_responses=interest_result.user_responses,
            interest_calculations=interest_result.calculations,
            generation_success=True,
            error=None
        )

    @staticmethod
    def _format_error_response(error_message: str) -> StrategyScenarioResult:
        """
        에러 발생 시 응답 포맷팅

        Args:
            error_message: 에러 메시지

        Returns:
            StrategyScenarioResult: 에러 응답
        """
        return StrategyScenarioResult(
            scenarios=[],
            user_conditions=EligibilityConditions(min_interest_rate=0.0),
            user_responses=[],
            interest_calculations=[],
            generation_success=False,
            error=error_message
        )

    @staticmethod
    def _validate_input(interest_result: InterestCalculatorResult) -> bool:
        """
        입력 데이터 검증

        Args:
            interest_result: InterestCalculatorTool 응답

        Returns:
            bool: 검증 성공 여부
        """
        if not interest_result.success:
            print("❌ InterestCalculatorTool 실행이 실패한 상태입니다.")
            return False

        if not interest_result.calculations:
            print("❌ 이자 계산 결과가 없습니다.")
            return False

        if not interest_result.user_conditions:
            print("❌ 사용자 조건이 없습니다.")
            return False

        if len(interest_result.calculations) < 3:
            print(f"⚠️ 계산된 상품이 {len(interest_result.calculations)}개로 부족합니다. 최소 3개 필요.")
            # 3개 미만이어도 진행은 가능하도록 warning만 출력

        return True

    def invoke(self, input_data: InterestCalculatorResult, config=None, **kwargs) -> StrategyScenarioResult:
        """
        Tool 실행 메인 로직 - Runnable 인터페이스

        Args:
            input_data: InterestCalculatorTool 응답
            config: 실행 설정 (선택)

        Returns:
            StrategyScenarioResult: 시나리오 생성 결과
        """
        print("🔄 StrategyScenarioTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_input(input_data):
            return self._format_error_response("입력 데이터 검증 실패")

        try:
            # 2. LLM 기반 시나리오 생성
            scenarios = self.generate_scenarios_with_llm(input_data)
            if not scenarios:
                return self._format_error_response("시나리오 생성에 실패했습니다.")

            print(f"🎯 {len(scenarios)}개 시나리오 생성 완료")

            # 3. 성공 응답 포맷팅
            return self._format_success_response(scenarios, input_data)

        except Exception as e:
            print(f"❌ StrategyScenarioTool 실행 중 오류: {str(e)}")
            return self._format_error_response(f"시나리오 생성 중 오류 발생: {str(e)}")