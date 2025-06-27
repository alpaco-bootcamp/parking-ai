"""
Tool 1: ConditionExtractorTool
역할: 우대조건 및 금리정보 청크 데이터 추출
"""
from typing import Optional

from langchain_core.runnables import Runnable, RunnableConfig
from pymongo import MongoClient

from common.data import NLP_CHUNKS_COLLECTION_NAME, MONGO_URI, DB_NAME
from schemas.agent_responses import EligibilitySuccessResponse
from schemas.question_filter_schema import (
    ExtractedProduct,
    ChunkData, ConditionExtractorResult,
)


class ConditionExtractorTool(Runnable):
    """
    우대조건 및 금리정보 청크 데이터를 추출하는 Tool

    출력: ConditionExtractorResult
    """

    def __init__(self):
        """
        Tool 초기화
        """
        client = MongoClient(MONGO_URI)
        self.db = client[DB_NAME]

    def extract_product_result(self, eligibility_response: EligibilitySuccessResponse) -> ConditionExtractorResult:
        """
        MongoDB에서 우대조건 및 금리정보 청크 데이터 조회 및 처리

        Args:
            eligibility_response: EligibilityAgent 응답

        Returns:
            ConditionExtractorResult: 우대조건 및 금리정보 청크 데이터 결과
        """
        try:
            collection = self.db[NLP_CHUNKS_COLLECTION_NAME]

            # 상품 코드 추출
            product_codes = [
                product.product_code
                for product in eligibility_response.result_products
            ]

            # 우대조건 및 금리정보 청크만 조회 (basic_rate_info, preferential_details)
            raw_chunks = list(
                collection.find(
                    {
                        "product_code": {"$in": product_codes},
                        "chunks.chunk_type": {
                            "$in": ["basic_rate_info", "preferential_details"]
                        },
                    }
                )
            )

            print(f"📋 조회된 우대조건 및 금리정보 청크: {len(raw_chunks)}개")

            # 스키마 형태로 데이터 변환
            processed_chunks = self._process_chunks_to_schema(raw_chunks)

            # 결과 통계 계산
            total_chunk_count = sum(len(chunk.chunks) for chunk in processed_chunks)

            result = ConditionExtractorResult(
                products=processed_chunks,
                total_products=len(processed_chunks),
                total_chunks=total_chunk_count,
                success=True,
            )

            return result

        except Exception as e:
            print(f"❌ 우대조건 및 금리정보 청크 조회 실패: {str(e)}")
            return ConditionExtractorResult(
                products=[], total_products=0, total_chunks=0, success=False
            )

    @staticmethod
    def _process_chunks_to_schema(raw_chunks: list[dict]) -> list[ExtractedProduct]:
        """
        MongoDB 원본 데이터를 스키마 형태로 변환

        Args:
            raw_chunks: MongoDB에서 조회된 원본 데이터

        Returns:
            list[RateConditionChunk]: 스키마 형태로 변환된 청크 데이터
        """
        processed_chunks = []

        for chunk_data in raw_chunks:
            # 우대조건 및 금리정보 청크만 필터링 및 스키마 변환
            filtered_chunks = []
            for chunk in chunk_data.get("chunks", []):
                if chunk.get("chunk_type") in [
                    "basic_rate_info",
                    "preferential_details",
                ]:
                    chunk_schema = ChunkData(
                        chunk_type=chunk.get("chunk_type", ""),
                        chunk_index=chunk.get("chunk_index", ""),
                        content_natural=chunk.get("content_natural", ""),
                    )
                    filtered_chunks.append(chunk_schema)

            if filtered_chunks:
                rate_condition_chunk = ExtractedProduct(
                    product_code=chunk_data.get("product_code", ""),
                    product_name=chunk_data.get("product_name", ""),
                    chunks=filtered_chunks,
                )
                processed_chunks.append(rate_condition_chunk)

        return processed_chunks

    @staticmethod
    def _validate_eligibility_data(
        eligibility_response: EligibilitySuccessResponse,
    ) -> bool:
        """
        EligibilityAgent 응답 데이터 검증

        Args:
            eligibility_response: EligibilityAgent 응답

        Returns:
            bool: 검증 성공 여부
        """
        if not eligibility_response.success:
            print("❌ EligibilityAgent 실행이 실패한 상태입니다.")
            return False

        if not eligibility_response.result_products:
            print("❌ 필터링된 상품이 없습니다.")
            return False

        return True

    def invoke(self, eligibility_response: EligibilitySuccessResponse, config=None,  **kwargs) -> ConditionExtractorResult:
        """
        Tool 실행 메인 로직 - Runnable 필수 메소드

        우대조건 및 금리정보 청크 데이터를 MongoDB에서 추출하여
        다음 단계(PatternAnalyzer)에서 사용할 수 있는 형태로 가공합니다.

        처리 과정:
        1. EligibilityAgent 응답 데이터 검증
        2. 상품 코드 기반 MongoDB 청크 데이터 조회
        3. basic_rate_info, preferential_details 청크만 필터링
        4. 스키마 형태로 데이터 변환

        Args:
            eligibility_response (EligibilitySuccessResponse): EligibilityAgent의 출력 결과
                - result_products: 1차 필터링된 통장 상품 목록
                - filter_summary: 필터링 통계 정보
                - user_conditions: 사용자 우대조건
            config (dict, optional): LangChain 실행 설정. Defaults to None.

        Returns:
            ConditionExtractorResult: 우대조건 및 금리정보 청크 데이터 결과
                - products: 추출된 상품별 청크 데이터 목록
                - total_products: 조회된 상품 수
                - total_chunks: 추출된 총 청크 수
                - success: 추출 성공 여부

        """
        print("🔄 ConditionExtractorTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_eligibility_data(eligibility_response):
            print("❌ EligibilityAgent 응답 데이터 검증 실패")
            return ConditionExtractorResult(
                products=[], total_products=0, total_chunks=0, success=False
            )

        # 2. 우대조건 및 금리정보 청크 데이터 조회 및 처리
        result = self.extract_product_result(eligibility_response)

        if not result.success:
            print("❌ 우대조건 및 금리정보 청크 조회 실패")
            return result

        print(
            f"✅ ConditionExtractorTool 실행 완료: {result.total_products}개 상품, {result.total_chunks}개 청크 추출"
        )
        return result