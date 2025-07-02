"""
조건 매칭 툴 - Rule-based 필터링
"""

from schemas.eligibility_conditions import EligibilityConditions
from schemas.eligibility_filter_result import EligibilityFilterResult


class ConditionMatcherTool:
    """Rule-based 조건 매칭 툴"""

    def __init__(self):
        """툴 초기화"""
        self.name = "condition_matcher"
        self.description = "사용자 조건과 통장 조건 Rule-based 매칭"

    @staticmethod
    def _check_interest_rate(product: dict, min_rate: float) -> bool:
        """
        금리 조건 체크

        Args:
            product: 상품 정보
            min_rate: 최소 금리

        Returns:
            bool: 금리 조건 충족 여부
        """
        basic_rate = product.get("interest_rate", 0)
        prime_rate = product.get("prime_interest_rate", 0)
        max_rate = max(basic_rate, prime_rate)
        return max_rate >= min_rate

    @staticmethod
    def _apply_category_filters(
        products: list[dict], categories: list[str]
    ) -> list[dict]:
        """
        카테고리 조건으로 순차 필터링

        Args:
            products: 상품 리스트
            categories: 필터링할 카테고리 리스트

        Returns:
            list[dict]: 필터링된 상품 리스트
        """
        filtered = products

        for category in categories:
            filtered = [
                product
                for product in filtered
                if category in product.get("categories", [])
            ]

        return filtered

    @staticmethod
    def _apply_special_condition_filters(
        products: list[dict], special_conditions: list[str]
    ) -> list[dict]:
        """
        우대조건으로 순차 필터링

        Args:
            products: 상품 리스트
            special_conditions: 필터링할 우대조건 리스트

        Returns:
            list[dict]: 필터링된 상품 리스트
        """
        filtered = products

        for condition in special_conditions:
            filtered = [
                product
                for product in filtered
                if product.get("special_conditions", {}).get(condition, False)
            ]

        return filtered

    @staticmethod
    def _apply_count_rebalancing(matched_products: list[dict], all_products: list[dict]) -> list[dict]:
        """
        금리 높은 순으로 정렬하여 15~30개로 개수 조정
        15개 미만일 경우 매칭된 상품 + 전체 데이터에서 추가 보충하여 총 15개
        30개 초과인 경우 금리 높은순으로 30개로 제한

        Args:
            matched_products: 3차 필터링까지 통과한 상품들
            all_products: 전체 상품 데이터 (15개 미만일 때 보충용)

        Returns:
            list[dict]: 리밸런싱된 상품 목록 (15~30개)
        """
        if not matched_products and not all_products:
            return []

        # 1. 매칭된 상품들을 prime_interest_rate 기준으로 정렬
        sorted_matched = sorted(
            matched_products,
            key=lambda x: x.get("prime_interest_rate", 0),
            reverse=True
        )

        # 2. 개수에 따른 처리
        if len(sorted_matched) < 15:
            # 15개 미만이면 부족한 개수만큼 전체 데이터에서 보충
            needed_count = 15 - len(sorted_matched)

            # 매칭된 상품의 product_code 집합 (중복 방지용)
            matched_codes = {product.get("product_code") for product in sorted_matched}

            # 전체 상품에서 매칭된 것 제외하고 정렬
            remaining_products = [
                product for product in all_products
                if product.get("product_code") not in matched_codes
            ]
            sorted_remaining = sorted(
                remaining_products,
                key=lambda x: x.get("prime_interest_rate", 0),
                reverse=True
            )

            # 매칭된 상품 + 부족한 개수만큼 추가
            return sorted_matched + sorted_remaining[:needed_count]

        elif len(sorted_matched) > 30:
            # 30개 초과면 상위 30개만
            return sorted_matched[:30]
        else:
            # 15~30개면 그대로
            return sorted_matched

    def run(
        self, conditions: EligibilityConditions, products: list[dict]
    ) -> EligibilityFilterResult:
        """
        조건 매칭 실행

        Args:
            conditions: 사용자 조건
            products: 상품 리스트

        Returns:
            EligibilityFilterResult: 필터링 결과
        """
        matched = []  # 조건 통과 상품
        excluded = []  # 조건 미달 상품
        exclusion_reasons = {}  # 상품별 제외 사유

        # 1차: 금리 필터링
        for product in products:
            product_code = product.get("product_code", "unknown")

            if not self._check_interest_rate(product, conditions.min_interest_rate):
                excluded.append(product)
                exclusion_reasons[product_code] = "최소 금리 기준 미달"
            else:
                matched.append(product)

        # 2차: 카테고리 필터링 (순차적으로 필터링)
        if conditions.categories:
            matched = self._apply_category_filters(matched, conditions.categories)

        # 3차: 우대조건 필터링 (순차적으로 필터링)
        if conditions.special_conditions:
            matched = self._apply_special_condition_filters(
                matched, conditions.special_conditions
            )

        # 🆕 4차: 개수 리밸런싱 (15~30개 조정)
        matched = self._apply_count_rebalancing(matched, products)


        # 제외된 상품 업데이트 (매칭에서 제외된 것들)
        matched_codes = {p.get("product_code") for p in matched}
        for product in products:
            product_code = product.get("product_code", "unknown")
            if (
                product_code not in matched_codes
                and product_code not in exclusion_reasons
            ):
                excluded.append(product)
                exclusion_reasons[product_code] = "카테고리 또는 우대조건 미충족"

        return EligibilityFilterResult.create_result(
            matched, excluded, exclusion_reasons, conditions
        )
