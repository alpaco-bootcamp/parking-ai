import pymongo
from db.save_db import get_all_documents
from common.data import BASIC_COLLECTION_NAME
from langchain.schema.runnable import RunnableLambda

from schemas.eligibility_conditions import EligibilityConditions
from schemas.agent_responses import (
    EligibilitySuccessResponse,
    EligibilityErrorResponse,
    FilterSummary,
)
from tools.condition_matcher import ConditionMatcherTool


class EligibilityAgent:
    """우대조건 기반 통장 필터링 에이전트"""

    def __init__(self, mongodb_client: pymongo.MongoClient) -> None:
        """
        에이전트 초기화

        Args:
            mongodb_client: MongoDB 클라이언트
        """
        self.db = mongodb_client
        self.condition_matcher = ConditionMatcherTool()
        # Runnable객체로 반환하여 파이프라인에서 실행시 execute(input_data)메소드 실행. 결과값이 다음 파이프라인에 전달
        self.runnable = RunnableLambda(self.execute)

        print("✅ EligibilityAgent 초기화 완료")

    @staticmethod
    def _format_error_response(error_message: str) -> EligibilityErrorResponse:
        """
        에러 발생 시 스키마 기반으로 응답 포맷팅

        Args:
            error_message: 에러 메시지

        Returns:
            EligibilityErrorResponse: 에러 응답 스키마
        """
        return EligibilityErrorResponse(error=error_message)

    @staticmethod
    def _format_success_response(
        filter_result, conditions: EligibilityConditions
    ) -> EligibilitySuccessResponse:
        """
        성공적인 필터링 결과를 스키마 기반으로 포맷팅

        Args:
            filter_result: ConditionMatcherTool의 실행 결과
            conditions: 파싱된 조건 데이터

        Returns:
            EligibilitySuccessResponse: 성공 응답 스키마
        """
        filter_summary = FilterSummary(
            total_analyzed=filter_result.total_analyzed,
            match_count=filter_result.match_count,
            excluded_count=len(filter_result.excluded_products),
            match_rate=filter_result.match_rate,
            execution_time=getattr(filter_result, "execution_time", None),
        )

        return EligibilitySuccessResponse(
            eligible_products=filter_result.matched_products,
            filter_summary=filter_summary,
            user_conditions=conditions,
        )

    def execute(
        self, input_data: dict[str, EligibilityConditions]
    ) -> EligibilitySuccessResponse | EligibilityErrorResponse:
        """
        에이전트 실행 - Runnable 인터페이스

        Args:
            input_data: 입력 데이터 딕셔너리
            - {"conditions": EligibilityConditions}

        Returns:
            EligibilitySuccessResponse | EligibilityErrorResponse: 필터링 결과
        """
        print("🚀 EligibilityAgent 실행 시작")

        conditions = input_data.get("conditions")
        if not conditions:
            return self._format_error_response("조건 데이터가 제공되지 않았습니다.")

        print(f"   📋 최소 금리: {conditions.min_interest_rate}%")
        print(f"   🏷️ 카테고리: {conditions.categories}")
        print(f"   🎁 우대조건: {conditions.special_conditions}")

        try:
            all_products = list(get_all_documents(BASIC_COLLECTION_NAME))
            print(f"   📊 분석 대상 상품: {len(all_products)}개")

            if not all_products:
                return self._format_error_response("분석할 상품 데이터가 없습니다.")

            print("   🔍 Rule-based 조건 매칭 실행 중...")
            filter_result = self.condition_matcher.run(
                conditions=conditions, products=all_products
            )

            print(f"   ✅ 조건 통과 상품: {filter_result.match_count}개")
            print(f"   ❌ 조건 미달 상품: {len(filter_result.excluded_products)}개")
            print(f"   📈 매칭률: {filter_result.match_rate:.1f}%")
            print(
                f"🎯 EligibilityAgent 실행 완료 - 적합 상품: {filter_result.match_count}개"
            )

            return self._format_success_response(filter_result, conditions)

        except Exception as e:
            print(f"❌ EligibilityAgent 실행 오류: {e}")
            return self._format_error_response(str(e))
