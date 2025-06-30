import time
from langchain.schema.runnable import RunnableLambda, RunnableSequence
from langchain_core.language_models import BaseLanguageModel

from context.question_agent_context import QuestionAgentContext
from tools.wrappers.question_tool_wrappers import QuestionTools
from schemas.agent_responses import (
    EligibilitySuccessResponse,
    QuestionErrorResponse, QuestionSuccessResponse,
)
from schemas.question_schema import PatternAnalyzerResult, UserInputResult


class QuestionAgent:
    """
    우대조건 질문을 통한 2차 필터링 에이전트

    처리 단계:
    1. ConditionExtractorTool: 우대조건 청크 데이터 추출
    2. PatternAnalyzerTool: LLM 기반 패턴 분석 및 RAG 쿼리 생성
    3. QuestionGeneratorTool: 패턴 분석 결과 기반으로 RAG 검색하여 사용자 질문 생성
    4. UserInputTool: 사용자 입력 처리
    """

    def __init__(self, llm: BaseLanguageModel, test_mode: bool = True):
        """
        Agent 초기화

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
            test_mode: 테스트 모드 여부 (콘솔/API 전환용)
        """
        self.llm = llm
        self.agent_ctx = QuestionAgentContext()  # Agent별 독립적인 context

        # Tools 초기화
        self.tools = QuestionTools.get_tools(llm, test_mode, self.agent_ctx)


        # Runnable 객체로 반환하여 파이프라인에서 실행
        self.runnable = RunnableLambda(self.execute)

        print(
            f"🔍 DEBUG: condition_extractor type: {type(self.tools.condition_extractor)}"
        )
        print(f"🔍 DEBUG: pattern_analyzer type: {type(self.tools.pattern_analyzer)}")
        print(f"🔍 DEBUG: runnable type: {type(self.runnable)}")

        print("✅ QuestionAgent 초기화 완료")

    def _build_runnable_chain(self) -> RunnableSequence:
        """
        RunnableSequence 체인 구성

        Returns:
            RunnableSequence: Tool들이 직접 연결된 Runnable 체인
        """
        return RunnableSequence(

            # EligibilitySuccessResponse → ConditionExtractorResult
            self.tools.condition_extractor, # Step 1: ConditionExtractor Tool 실행
            # ConditionExtractorResult → PatternAnalyzerResult
            self.tools.pattern_analyzer, # Step 2: PatternAnalyzer Tool 실행
            # PatternAnalyzerResult → QuestionGeneratorResult
            self.tools.question_generator, # Step 3: QuestionGenerator Tool 실행
            # QuestionGeneratorResult → UserInputResult
            self.tools.user_input, # Step 4: UserInput Tool 실행
            # UserInputResult → QuestionSuccessResponse
            self.tools.response_formatter, # Step 5: ResponseFormatter Tool 실행

        )

    @staticmethod
    def _format_error_response(error_message: str) -> QuestionErrorResponse:
        """
        에러 발생 시 표준 응답 포맷으로 변환

        Args:
            error_message: 에러 메시지

        Returns:
            QuestionErrorResponse: 표준화된 에러 응답
        """
        return QuestionErrorResponse(error=error_message)

    def execute(
        self, eligibility_response: EligibilitySuccessResponse
    ) -> QuestionSuccessResponse | QuestionErrorResponse:
        """
        Agent 실행

        Args:
            eligibility_response: EligibilityAgent의 출력 결과

        Returns:
            QuestionSuccessResponse | QuestionErrorResponse: 사용자 질문-답변 데이터 + 적격 통장 목록
        """
        start_time = time.time()
        print("🚀 QuestionAgent 실행 시작")

        try:
            # 입력 데이터 검증
            if not eligibility_response.success:
                raise ValueError("EligibilityAgent 실행이 실패한 상태입니다.")

            if not eligibility_response.result_products:
                raise ValueError("필터링된 상품이 없습니다.")

            print(
                f"✅ 입력 검증 완료: {len(eligibility_response.result_products)}개 상품"
            )

            # Context에 데이터 설정
            self.agent_ctx.set_eligible_products(eligibility_response.result_products)
            print(f"agent ids: {id(self.agent_ctx)}")
            self.agent_ctx.set_user_conditions(eligibility_response.user_conditions)
            print(f"eligibility_response.user_conditions: {eligibility_response.user_conditions}")
            self.agent_ctx.set_session_id(f"session_{int(start_time)}")

            tool_chain = self._build_runnable_chain()
            result = tool_chain.invoke(eligibility_response)

            execution_time = time.time() - start_time
            print(
                f"✅ QuestionAgent 실행 완료 (소요시간: {execution_time:.2f}초)"
            )

            # 🔥 최종 정보
            if hasattr(result, 'collection_success'):
                print(
                    f"📊 사용자 입력 결과: {result.answered_questions}/{result.total_questions}개 질문 응답 완료"
                )
                print(f"응답 요약: {result.response_summary}")
            return result

        except Exception as e:
            error_msg = f"QuestionAgent RunnableSequence 실행 오류: {str(e)}"
            print(f"❌ {error_msg}")
            return self._format_error_response(error_msg)
