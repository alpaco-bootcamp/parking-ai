# tests/run_pipeline_test.py
"""
파이프라인 실행 테스트 스크립트
실제 MongoDB 연결을 통해 파이프라인을 테스트합니다.
"""

import sys
import os
from pymongo import MongoClient

from pipeline.pipeline import Pipeline

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.eligibility_conditions import EligibilityConditions
from schemas.agent_responses import EligibilitySuccessResponse, EligibilityErrorResponse
from common.data import MONGO_URI


def create_test_conditions() -> list[EligibilityConditions]:
    """다양한 테스트 조건들 생성"""

    # 테스트 케이스 1: 높은 금리, 특별 오퍼
    test_case_1 = EligibilityConditions(
        min_interest_rate=1.0,
        categories=["specialOffer", "online"],
        special_conditions=["first_banking"],
    )

    # 테스트 케이스 2: 낮은 금리, 일반 조건
    test_case_2 = EligibilityConditions(
        min_interest_rate=2.0,
        categories=["anyone"],
        special_conditions=["bank_app", "using_card"],
    )

    # 테스트 케이스 3: 매우 높은 금리, 모든 조건 (매칭되는 상품이 적을 것으로 예상)
    test_case_3 = EligibilityConditions(
        min_interest_rate=6.0,
        categories=["specialOffer"],
        special_conditions=[
            "first_banking",
            "bank_app",
            "online",
            "using_salary_account",
            "using_utility_bill",
            "using_card",
        ],
    )

    return [test_case_1, test_case_2, test_case_3]


def run_pipeline_test():
    """파이프라인 테스트 실행"""

    print("🚀 파킹통장 추천 파이프라인 테스트 시작")
    print("=" * 60)

    try:
        # 파이프라인 초기화
        pipeline = Pipeline()

        # 파이프라인 정보 출력
        info = pipeline.get_pipeline_info()
        print(f"📊 파이프라인 정보:")
        print(f"   - 현재 에이전트: {info['current_agents']}")
        print(f"   - 계획된 에이전트: {info['planned_agents']}")
        print(f"   - 상태: {info['pipeline_status']}")
        print()

        # 테스트 조건들 생성
        test_condition_list = create_test_conditions()

        # 각 테스트 케이스 실행
        for i, test_condition in enumerate(test_condition_list, 1):
            print(f"🧪 테스트 케이스 {i} 실행")
            print(
                f"   조건: 최소금리 {test_condition.min_interest_rate}%, "
                f"카테고리 {test_condition.categories}"
            )
            print(f"   우대조건: {test_condition.special_conditions}")

            # 파이프라인 실행
            result = pipeline.run(test_condition)

            # 결과 출력
            if isinstance(result, EligibilitySuccessResponse):
                print(f"   ✅ 성공: {result.filter_summary.match_count}개 상품 매칭")
                print(f"   📈 매칭률: {result.filter_summary.match_rate:.1f}%")
                print(f"   🎯 다음 에이전트: {result.next_agent}")

                # 매칭된 상품 일부 출력
                if result.result_products:
                    print(f"   📋 매칭된 상품:")
                    for product in result.result_products:
                        print(f" 상품: {product.product_name} ")

            elif isinstance(result, EligibilityErrorResponse):
                print(f"   ❌ 오류: {result.error}")

            print("-" * 60)

        print("🎯 모든 테스트 케이스 완료")

    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


def run_single_test():
    """단일 테스트 케이스 실행 (디버깅용)"""

    print("🧪 단일 테스트 케이스 실행")

    try:
        # MongoDB 연결
        pipeline = Pipeline()

        # 간단한 테스트 조건
        test_conditions = EligibilityConditions(
            min_interest_rate=1.0,
            categories=[],
            special_conditions=["bank_app"],
        )

        print(f"📝 테스트 조건: {test_conditions}")

        # 파이프라인 실행
        result = pipeline.run(test_conditions)

        # 상세 결과 출력
        print("\n📊 실행 결과:")
        # 결과 출력
        if isinstance(result, EligibilitySuccessResponse):
            print(f"   ✅ 성공: {result.filter_summary.match_count}개 상품 매칭")
            print(f"   📈 매칭률: {result.filter_summary.match_rate:.1f}%")
            print(f"   🎯 다음 에이전트: {result.next_agent}")

            # 매칭된 상품 일부 출력
            if result.result_products:
                print(f"   📋 매칭된 상품:")
                for product in result.result_products:
                    print(f" 상품: {product.product_name} ")

        elif isinstance(result, EligibilityErrorResponse):
            print(f"   ❌ 오류: {result.error}")

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":

    run_single_test() # 단일 테스트
    # run_pipeline_test()  # 총 테스트 케이스 테스트
