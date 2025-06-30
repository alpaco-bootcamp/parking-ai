"""
Tool 4: UserInputTool
역할: 환경별 적응형 사용자 입력 처리 (콘솔/API 자동 전환)
"""

import uuid
from datetime import datetime
from langchain.schema.runnable import Runnable

from schemas.question_filter_schema import UserResponse, UserInputResult, QuestionGeneratorResult, UserQuestion


def _get_api_input(question: str, question_id: str) -> tuple[str, bool]:
    """
    FastAPI WebSocket을 통한 사용자 입력 받기 (test_mode=False)

    Args:
        question: 사용자에게 보여줄 질문
        question_id: 질문 ID

    Returns:
        tuple[str, bool]: (원본응답, boolean값)

    Note:
        현재는 Mock 구현, 추후 실제 WebSocket 연동 예정
    """
    print(f"🌐 API 모드에서 질문 대기 중: {question_id}")
    print(f"📤 질문 전송: {question}")

    # TODO: 실제 FastAPI WebSocket 구현
    # 현재는 기본값 반환
    print("⚠️  API 모드는 아직 구현되지 않음. 기본값(True) 반환")
    return "api_default", True


def _create_response_summary(self, responses: list[UserResponse]) -> dict[str, bool]:
    """
    질문별 응답 요약 딕셔너리 생성 (Tool 6에서 필터링 기준으로 사용)

    Args:
        responses: 사용자 응답 목록

    Returns:
        dict[str, bool]: 질문 텍스트별 조건 충족 여부 (question -> response_value)
    """
    summary = {}

    for response in responses:
        summary[response.question] = response.response_value

    return summary


class UserInputTool(Runnable):
    """
    환경별 적응형 사용자 입력 처리 Tool

    기능:
    - test_mode=True: 콘솔에서 y/n 입력 받기
    - test_mode=False: FastAPI WebSocket 대기 (향후 구현)
    """

    def __init__(self, test_mode: bool = True):
        """
        Tool 초기화

        Args:
            test_mode: 테스트 모드 여부 (True: 콘솔, False: API)
        """
        super().__init__()
        self.test_mode = test_mode
        self.session_id = str(uuid.uuid4())

        print(f"🔧 UserInputTool 초기화 완료 (test_mode={test_mode})")

    @staticmethod
    def _get_console_input(question: str, question_id: str) -> tuple[str, bool]:
        """
        콘솔에서 사용자 입력 받기 (test_mode=True)

        Args:
            question: 사용자에게 보여줄 질문
            question_id: 질문 ID

        Returns:
            tuple[str, bool]: (원본응답, boolean값)
        """
        print(f"\n{'=' * 60}")
        print(f"📋 질문 {question_id}")
        print(f"❓ {question}")
        print(f"{'=' * 60}")

        while True:
            try:
                user_input = input("👤 답변 (y/n): ").strip().lower()

                if user_input in ['y', 'yes', '예', '네', '1', 'true']:
                    return user_input, True
                elif user_input in ['n', 'no', '아니오', '아님', '0', 'false']:
                    return user_input, False
                else:
                    print("⚠️  'y' 또는 'n'으로 답변해주세요.")
                    continue

            except KeyboardInterrupt:
                print("\n🛑 사용자가 입력을 중단했습니다.")
                return "interrupted", False
            except Exception as e:
                print(f"❌ 입력 처리 중 오류: {str(e)}")
                continue

    @staticmethod
    def _create_user_response(
            question: UserQuestion,
            raw_response: str,
            response_value: bool
    ) -> UserResponse:
        """
        UserResponse 객체 생성

        Args:
            question: 원본 질문 객체 (UserQuestion)
            raw_response: 원본 응답
            response_value: boolean 값

        Returns:
            UserResponse: 사용자 응답 객체
        """
        return UserResponse(
            # UserQuestion 필드들 언패킹
            id=question.id,
            category=question.category,
            question=question.question,
            impact=question.impact,

            # UserResponse 추가 필드
            response_value=response_value,
            raw_response=raw_response,
            response_timestamp=datetime.now()
        )

    @staticmethod
    def _validate_input(question_generator_result: QuestionGeneratorResult) -> bool:
        """
        입력 데이터 검증

        Args:
            question_generator_result: Tool 3의 출력 결과

        Returns:
            bool: 검증 성공 여부
        """
        if not question_generator_result.generation_success:
            print("❌ QuestionGeneratorTool 실행이 실패한 상태입니다.")
            return False

        if not question_generator_result.questions:
            print("❌ 생성된 질문이 없습니다.")
            return False

        if len(question_generator_result.questions) == 0:
            print("❌ 질문 목록이 비어있습니다.")
            return False

        return True

    def invoke(
            self,
            input_data: QuestionGeneratorResult,
            config=None,
            **kwargs
    ) -> UserInputResult:
        """
        Runnable 인터페이스 구현

        Args:
            input_data: Tool 3의 출력 결과 (QuestionGeneratorResult)
            config: 실행 설정 (사용되지 않음)

        Returns:
            UserInputResult: 사용자 입력 수집 결과
        """
        print("🚀 UserInputTool 실행 시작")
        start_time = datetime.now()

        user_responses = []
        clarification_count = 0

        # 1. 입력 데이터 검증
        if not self._validate_input(input_data):
            return UserInputResult(
                user_responses=[],
                response_summary={},
                total_questions=0,
                answered_questions=0,
                collection_success=False
            )

        try:
            # 2. 질문 개요 출력
            print(f"\n🎯 총 {input_data.total_questions}개의 질문에 답변해주세요.")
            print(f"🆔 세션 ID: {self.session_id}")


            # 3. 각 질문별 사용자 응답 수집
            for i, question in enumerate(input_data.questions, 1):
                print(f"\n🔄 질문 {i}/{input_data.total_questions} 처리 중")

                try:
                    # 환경별 입력 처리
                    if self.test_mode:
                        raw_response, response_value = self._get_console_input(
                            question.question, question.id
                        )
                    else:
                        raw_response, response_value = _get_api_input(
                            question.question, question.id
                        )

                    # UserResponse 객체 생성 (question 객체 전체 전달)
                    user_response = self._create_user_response(
                        question=question,
                        raw_response=raw_response,
                        response_value=response_value
                    )

                    user_responses.append(user_response)

                    print(f"✅ {question.id} 응답 완료: {response_value}")

                except Exception as e:
                    print(f"❌ 질문 {question.id} 처리 실패: {str(e)}")
                    clarification_count += 1
                    continue

            # 4. 응답 요약 생성
            response_summary = _create_response_summary(user_responses)

            # 5. 실행 시간 계산
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            # 6. 결과 생성
            result = UserInputResult(
                user_responses=user_responses,
                response_summary=response_summary,
                total_questions=input_data.total_questions,
                answered_questions=len(user_responses),
                collection_success=len(user_responses) > 0
            )

            # 7. 결과 요약 출력
            print(f"\n{'=' * 60}")
            print(f"🎉 사용자 입력 수집 완료!")
            print(f"📊 응답 완료: {len(user_responses)}/{input_data.total_questions}")
            print(f"⏱️  소요 시간: {total_time:.1f}초")
            print(f"📋 카테고리별 요약:")
            for category, value in response_summary.items():
                status = "✅ 충족" if value else "❌ 미충족"
                print(f"   • {category}: {status}")
            print(f"{'=' * 60}")

            return result

        except Exception as e:
            print(f"❌ UserInputTool 실행 실패: {str(e)}")

            # 실패 시에도 부분 결과 반환
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()

            return UserInputResult(
                user_responses=user_responses,
                response_summary={},
                total_questions=input_data.total_questions,
                answered_questions=len(user_responses) if 'user_responses' in locals() else 0,
                collection_success=False
            )

