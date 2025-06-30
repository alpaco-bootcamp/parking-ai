"""
Contextvar를 사용한 Agent - Tool 간 데이터 공유 시스템
"""

from contextvars import ContextVar
from typing import Any
from schemas.agent_responses import SimpleProduct
from schemas.eligibility_conditions import EligibilityConditions


class QuestionAgentContext:
    """
    Contextvar를 활용한  Agent - Tool 간 데이터 공유 매니저

    특징:
    - Thread-safe: 멀티스레드 환경에서 안전
    - Async-safe: 비동기 환경에서 안전
    - 타입 안전성: 완벽한 타입 힌팅 지원
    - 메모리 효율: 필요한 데이터만 저장
    """

    def __init__(self):
        """AgentContext 인스턴스 초기화"""
        self.eligible_products_ctx: ContextVar[list[SimpleProduct]] = ContextVar(
            'eligible_products',
            default=[]
        )

        self.user_conditions_ctx: ContextVar[EligibilityConditions | None] = ContextVar(
            'user_conditions',
            default=None
        )

        self.session_id_ctx: ContextVar[str] = ContextVar(
            'session_id',
            default=''
        )

    def set_eligible_products(self, products: list[SimpleProduct]) -> None:
        """
        1차 필터링된 적격 통장 목록 설정

        Args:
            products: EligibilityAgent에서 필터링된 통장 목록
        """
        self.eligible_products_ctx.set(products)
        print(f"🏦 Context에 적격 통장 {len(products)}개 저장됨")

    def get_eligible_products(self) -> list[SimpleProduct]:
        """
        적격 통장 목록 조회

        Returns:
            list[SimpleProduct]: 저장된 통장 목록
        """
        products = self.eligible_products_ctx.get()
        print(f"🏦 Context에서 적격 통장 {len(products)}개 조회됨")
        return products

    def set_user_conditions(self, conditions: EligibilityConditions) -> None:
        """
        사용자 조건 정보 설정

        Args:
            conditions: 사용자가 입력한 우대조건 정보
        """
        self.user_conditions_ctx.set(conditions)
        print(f"👤 Context에 사용자 조건 저장중 (조건: {conditions})")
        # print(f"👤 Context에 사용자 조건 저장됨 (예산: {conditions.budget:,}원)")

    def get_user_conditions(self) -> EligibilityConditions | None:
        """
        사용자 조건 정보 조회

        Returns:
            EligibilityConditions | None: 저장된 사용자 조건
        """
        conditions = self.user_conditions_ctx.get()
        if conditions:
            print(f"👤Context에 서 사용자 조건 조회됨 (예산: {conditions}원)")
        else:
            print("⚠️ Context에 사용자 조건이 없음")
        return conditions

    def set_session_id(self, session_id: str) -> None:
        """
        세션 ID 설정

        Args:
            session_id: 현재 세션의 고유 ID
        """
        self.session_id_ctx.set(session_id)
        print(f"🆔 세션 ID 설정됨: {session_id}")

    def get_session_id(self) -> str:
        """
        세션 ID 조회

        Returns:
            str: 현재 세션 ID
        """
        return self.session_id_ctx.get()

    def clear_context(self) -> None:
        """
        모든 Context 데이터 초기화

        Note: 새로운 요청 시작 시 호출하여 이전 데이터 정리
        """
        self.eligible_products_ctx.set([])
        self.user_conditions_ctx.set(None)
        self.session_id_ctx.set('')
        print("🔄 Agent Context 모든 데이터 초기화됨")

    def get_context_info(self) -> dict[str, Any]:
        """
        현재 Context 상태 정보 조회 (디버깅용)

        Returns:
            dict: Context 상태 정보
        """
        return {
            "eligible_products_count": len(self.eligible_products_ctx.get()),
            "has_user_conditions": self.user_conditions_ctx.get() is not None,
            "session_id": self.session_id_ctx.get(),
            "context_status": "active" if self.session_id_ctx.get() else "empty"
        }