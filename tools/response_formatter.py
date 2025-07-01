"""
Tool 5: ResponseFormatterTool
역할: QuestionAgent의 최종 출력 포맷팅 (StrategyAgent 입력용)
"""

from langchain.schema.runnable import Runnable

from context.question_agent_context import QuestionAgentContext
from schemas.agent_responses import QuestionSuccessResponse, QuestionErrorResponse
from schemas.question_tool_schema import UserInputResult


class ResponseFormatterTool(Runnable):
    """
    QuestionAgent의 최종 응답을 StrategyAgent용으로 포맷팅하는 Tool

    기능:
    - UserInputResult + Context 데이터를 통합
    - StrategyAgent가 필요한 완전한 데이터셋 생성
    """

    def __init__(self, agent_ctx: QuestionAgentContext):
        """
        Tool 초기화
        """

        super().__init__()
        print("✅ ResponseFormatterTool 초기화 완료")
        self.agent_ctx = agent_ctx
        print(f"agent ids: {id(self.agent_ctx)}")

    @staticmethod
    def _validate_input(input_data: UserInputResult) -> bool:
        """
        입력 데이터 검증

        Args:
            input_data: UserInputTool의 출력 결과

        Returns:
            bool: 검증 성공 여부
        """
        if not input_data.collection_success:
            print("❌ 사용자 입력 수집이 실패한 상태입니다.")
            return False

        if not input_data.user_responses:
            print("❌ 사용자 응답이 없습니다.")
            return False

        if input_data.answered_questions == 0:
            print("❌ 답변된 질문이 없습니다.")
            return False

        return True

    def invoke(
        self, input_data: UserInputResult, config=None, **kwargs
    ) -> QuestionSuccessResponse | QuestionErrorResponse:
        """
        Runnable 인터페이스 구현

        Args:
            input_data: Tool 4의 출력 결과 (UserInputResult)
            config: 실행 설정 (사용되지 않음)

        Returns:
            QuestionSuccessResponse | QuestionErrorResponse: 실행 결과
        """
        print("🚀 ResponseFormatterTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_input(input_data):
            return QuestionErrorResponse(error="사용자 입력 데이터 검증 실패")

        try:
            # 2. Context에서 데이터 조회
            eligible_products = self.agent_ctx.get_eligible_products()

            user_conditions = self.agent_ctx.get_user_conditions()

            if not eligible_products:
                print("⚠️ Context에서 eligible_products를 찾을 수 없습니다.")
                return QuestionErrorResponse(
                    error="Context에서 적격 통장 목록을 찾을 수 없음"
                )

            if not user_conditions:
                print("⚠️ Context에서 user_conditions를 찾을 수 없습니다.")
                return QuestionErrorResponse(
                    error="Context에서 사용자 조건을 찾을 수 없음"
                )

            print(
                f"📋 Context에서 데이터 조회 완료: 통장 {len(eligible_products)}개, 응답 {len(input_data.user_responses)}개"
            )

            # 3. 최종 응답 생성
            response = QuestionSuccessResponse(
                eligible_products=eligible_products,
                user_responses=input_data.user_responses,
                response_summary=input_data.response_summary,
                user_conditions=user_conditions,
                processing_step="question_filter_completed",
                next_agent="StrategyAgent",
                success=True,
                error=None,
            )

            print("✅ ResponseFormatterTool 실행 완료")
            print(f"🎯 다음 단계: {response.next_agent}")
            print(
                f"📊 최종 데이터: 통장 {len(response.eligible_products)}개, 응답 {len(response.user_responses)}개"
            )

            return response

        except Exception as e:
            print(f"❌ ResponseFormatterTool 실행 실패: {str(e)}")
            return QuestionErrorResponse(error=f"응답 포맷팅 실패: {str(e)}")
