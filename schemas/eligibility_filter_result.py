"""
필터링 결과 스키마 정의
"""
from pydantic import BaseModel
from datetime import datetime


class EligibilityFilterResult(BaseModel):
    """필터링 결과"""
    matched_products: list[dict]  # 조건 통과 상품
    excluded_products: list[dict]  # 조건 미달 상품
    total_analyzed: int  # 총 분석 상품 수
    match_count: int  # 매칭된 상품 수
    match_rate: float  # 매칭률
    exclusion_reasons: dict[str, str]  # 상품별 제외 사유
    processing_timestamp: str  # 처리 시간
    filter_conditions: dict  # 필터링 조건 요약

    @classmethod
    def create_result(cls, matched: list[dict], excluded: list[dict],
                      exclusion_reasons: dict[str, str], conditions) -> "FilterResult":
        """
        필터링 결과 생성

        Args:
            matched: 매칭된 상품 리스트
            excluded: 제외된 상품 리스트
            exclusion_reasons: 제외 사유
            conditions: 사용자 조건

        Returns:
            FilterResult: 완성된 결과 객체
        """
        total = len(matched) + len(excluded)
        match_rate = (len(matched) / total * 100) if total > 0 else 0

        return cls(
            matched_products=matched,
            excluded_products=excluded,
            total_analyzed=total,
            match_count=len(matched),
            match_rate=match_rate,
            exclusion_reasons=exclusion_reasons,
            processing_timestamp=datetime.now().isoformat(),
            filter_conditions={
                "min_interest_rate": conditions.min_interest_rate,
                "categories": conditions.categories,
                "special_conditions": conditions.special_conditions
            }
        )