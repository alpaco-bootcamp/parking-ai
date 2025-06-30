import time
from langchain.schema.runnable import RunnableLambda, RunnableSequence
from langchain_core.language_models import BaseLanguageModel

from tools.wrappers.question_filter_tool_wrappers import QuestionFilterTools
from schemas.agent_responses import (
    EligibilitySuccessResponse,
    QuestionFilterErrorResponse,
)
from schemas.question_filter_schema import PatternAnalyzerResult


class QuestionFilterAgent:
    """
    우대조건 질문을 통한 2차 필터링 에이전트

    처리 단계:
    1. ConditionExtractorTool: 우대조건 청크 데이터 추출
    2. PatternAnalyzerTool: LLM 기반 패턴 분석 및 RAG 쿼리 생성
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Agent 초기화

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
        """
        self.llm = llm
        # Tools 초기화
        self.tools = QuestionFilterTools.get_tools(llm)

        # Runnable 객체로 반환하여 파이프라인에서 실행
        self.runnable = RunnableLambda(self.execute)

        print(
            f"🔍 DEBUG: condition_extractor type: {type(self.tools.condition_extractor)}"
        )
        print(f"🔍 DEBUG: pattern_analyzer type: {type(self.tools.pattern_analyzer)}")
        print(f"🔍 DEBUG: runnable type: {type(self.runnable)}")

        print("✅ QuestionFilterAgent 초기화 완료")

    def _build_runnable_chain(self) -> RunnableSequence:
        """
        RunnableSequence 체인 구성

        Returns:
            RunnableSequence: Tool들이 직접 연결된 Runnable 체인
        """
        return RunnableSequence(
            # Step 1: ConditionExtractor Tool 실행
            # EligibilitySuccessResponse → ConditionExtractorResult
            self.tools.condition_extractor,
            # Step 2: PatternAnalyzer Tool 실행
            # ConditionExtractorResult → PatternAnalyzerResult
            self.tools.pattern_analyzer,
        )

    @staticmethod
    def _format_error_response(error_message: str) -> QuestionFilterErrorResponse:
        """
        에러 발생 시 표준 응답 포맷으로 변환

        Args:
            error_message: 에러 메시지

        Returns:
            QuestionFilterErrorResponse: 표준화된 에러 응답
        """
        return QuestionFilterErrorResponse(error=error_message)

    def execute(
        self, eligibility_response: EligibilitySuccessResponse
    ) -> PatternAnalyzerResult | QuestionFilterErrorResponse:
        """
        Agent 실행

        Args:
            eligibility_response: EligibilityAgent의 출력 결과

        Returns:
            PatternAnalyzerResult | QuestionFilterErrorResponse: 패턴 분석 결과
        """
        start_time = time.time()
        print("🚀 QuestionFilterAgent 실행 시작")

        try:
            # 입력 데이터 검증
            if not eligibility_response.success:
                raise ValueError("EligibilityAgent 실행이 실패한 상태입니다.")

            if not eligibility_response.result_products:
                raise ValueError("필터링된 상품이 없습니다.")

            print(
                f"✅ 입력 검증 완료: {len(eligibility_response.result_products)}개 상품"
            )

            # RunnableSequence 체인 실행 (Step 1 → Step 2)
            # result = self.runnable.invoke(eligibility_response)

            tool_chain = self._build_runnable_chain()
            result = tool_chain.invoke(eligibility_response)

            execution_time = time.time() - start_time
            print(
                f"✅ QuestionFilterAgent 실행 완료 (소요시간: {execution_time:.2f}초)"
            )

            # 🔥 최종 정보
            if isinstance(result, PatternAnalyzerResult):
                print(
                    f"📊 패턴 분석 결과: {result.total_patterns}개 패턴, {len(result.rag_queries)}개 RAG 쿼리 생성"
                )
                print(f"analysis_patterns: {result.analysis_patterns}")
                print(f"rag_queries: {result.rag_queries}")
            return result

        except Exception as e:
            error_msg = f"QuestionFilterAgent RunnableSequence 실행 오류: {str(e)}"
            print(f"❌ {error_msg}")
            return self._format_error_response(error_msg)
