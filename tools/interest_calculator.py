"""
InterestCalculatorTool
역할: LLM 기반 파킹통장 이자 계산 도구
"""

from datetime import datetime
from langchain.schema.runnable import Runnable
from langchain_core.language_models import BaseLanguageModel
from pymongo import MongoClient

from common.data import NLP_CHUNKS_COLLECTION_NAME, MONGO_URI, DB_NAME
from schemas.agent_responses import QuestionSuccessResponse, SimpleProduct
from schemas.strategy_tool_schema import (
    InterestCalculatorResult,
    ProductInterestCalculation, ProductDetailInfo, InterestCalculationOutput,
)
from schemas.eligibility_conditions import EligibilityConditions
from prompts.strategy_prompts import StrategyPrompts


class InterestCalculatorTool(Runnable):
    """
    LLM 기반 파킹통장 이자 계산 Tool

    입력: QuestionSuccessResponse
    출력: InterestCalculatorResult
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Tool 초기화

        Args:
            llm: 사용할 llm모델
        """
        super().__init__()
        self.llm = llm
        client = MongoClient(MONGO_URI)
        self.db = client[DB_NAME]

        print("✅ InterestCalculatorTool 초기화 완료")

    def extract_product_details(self, eligible_products: list[SimpleProduct]) -> list[ProductDetailInfo]:
        """
        MongoDB에서 상품별 필요한 데이터만 선택적 추출

        Args:
            eligible_products: 적격 상품 목록

        Returns:
            list[ProductDetailInfo]: 상품별 금리정보 및 우대조건 데이터
        """
        try:
            collection = self.db[NLP_CHUNKS_COLLECTION_NAME]

            product_codes: list[str] = [product.product_code for product in eligible_products]

            # product_code, product_name, chunks.chunk_type, chunks.content_natural 필드만 선택적으로 조회
            pipeline = [
                {
                    "$match": {
                        "product_code": {"$in": product_codes},
                        "chunks.chunk_type": {"$in": ["basic_rate_info", "preferential_details"]}
                    }
                },
                {
                    "$project": {
                        "product_code": 1,
                        "product_name": 1,
                        "chunks": {
                            "$filter": {
                                "input": "$chunks",
                                "cond": {
                                    "$in": ["$$this.chunk_type", ["basic_rate_info", "preferential_details"]]
                                }
                            }
                        }
                    }
                },
                {
                    "$project": {
                        "product_code": 1,
                        "product_name": 1,
                        "chunks.chunk_type": 1,
                        "chunks.content_natural": 1
                    }
                }
            ]

            filtered_data = list(collection.aggregate(pipeline))

            # 스키마로 변환
            product_details: list[ProductDetailInfo] = [
                ProductDetailInfo(**data) for data in filtered_data
            ]

            return product_details

        except Exception as e:
            print(f"❌ 상품 상세 정보 추출 실패: {str(e)}")
            return []

    def calculate_with_llm(
            self,
            product_details: list[ProductDetailInfo],
            question_response: QuestionSuccessResponse
    ) -> list[ProductInterestCalculation]:
        """
        LLM을 사용하여 상품별 이자 계산 (배치 처리)

        Args:
            product_details: 상품별 상세 정보
            question_response: 사용자 조건 및 응답

        Returns:
            list[ProductInterestCalculation]: 계산 결과 목록
        """
        try:
            from langchain.prompts import PromptTemplate
            from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
            from langchain.output_parsers import PydanticOutputParser

            batch_size = 3  # 배치 크기 (한 번에 [batch_size]개 상품씩 처리)
            all_calculations: list[ProductInterestCalculation] = []

            # 배치별로 처리
            for i in range(0, len(product_details), batch_size):
                batch_products = product_details[i:i + batch_size]

                print(
                    f"🔄 배치 {i // batch_size + 1}/{(len(product_details) + batch_size - 1) // batch_size} 처리 중 ({len(batch_products)}개 상품)")

                # 1. 프롬프트 생성
                prompts = StrategyPrompts()
                prompt_text = prompts.create_interest_calculation_prompt(
                    product_details=batch_products,
                    user_conditions=question_response.user_conditions,
                    user_responses=question_response.user_responses
                )

                # 2. OutputParser 설정
                output_parser = PydanticOutputParser(pydantic_object=InterestCalculationOutput)

                prompt_template = PromptTemplate(
                    template=prompt_text + "\n\n{format_instructions}",
                    input_variables=[],
                    partial_variables={
                        "format_instructions": output_parser.get_format_instructions()
                    },
                )

                print(f"🤖 배치 {i // batch_size + 1} LLM 이자 계산 중...")

                # 3. LCEL 체이닝 구성
                chain = (
                        RunnablePassthrough()
                        | prompt_template
                        | self.llm
                        | output_parser
                        | RunnableLambda(self._convert_calculation_to_schema)
                )

                # 4. 체인 실행
                batch_result = chain.invoke({})

                if batch_result:
                    all_calculations.extend(batch_result)
                    print(f"✅ 배치 {i // batch_size + 1} 완료: {len(batch_result)}개 상품 계산")
                else:
                    print(f"⚠️ 배치 {i // batch_size + 1} 실패")

            print(f"🎯 전체 계산 완료: {len(all_calculations)}개 상품")
            return all_calculations

        except Exception as e:
            print(f"❌ LLM 이자 계산 실패: {str(e)}")
            return []

    @staticmethod
    def _convert_calculation_to_schema(llm_output: InterestCalculationOutput) -> list[ProductInterestCalculation]:
        """
        LLM 파싱된 출력을 최종 결과 스키마로 변환

        Args:
            llm_output: Pydantic OutputParser로 파싱된 LLM 출력

        Returns:
            list[ProductInterestCalculation]: 최종 계산 결과
        """
        try:
            return llm_output.calculations

        except Exception as e:
            print(f"❌ 계산 결과 스키마 변환 실패: {str(e)}")
            return []

    @staticmethod
    def _format_success_response(
            calculations: list[ProductInterestCalculation],
            question_response: QuestionSuccessResponse
    ) -> InterestCalculatorResult:
        """
        성공적인 계산 결과 포맷팅

        Args:
            calculations: 계산 결과 목록
            question_response: 원본 질문 응답

        Returns:
            InterestCalculatorResult: 성공 응답
        """

        return InterestCalculatorResult(
            calculations=calculations,
            user_responses=question_response.user_responses,
            total_products_calculated=len(calculations),
            user_conditions=question_response.user_conditions,
            calculation_timestamp=datetime.now().isoformat(),
            success=True,
            error=None
        )

    @staticmethod
    def _format_error_response(error_message: str) -> InterestCalculatorResult:
        """
        에러 발생 시 응답 포맷팅

        Args:
            error_message: 에러 메시지

        Returns:
            InterestCalculatorResult: 에러 응답
        """

        return InterestCalculatorResult(
            calculations=[],
            user_responses=[],
            total_products_calculated=0,
            user_conditions=EligibilityConditions(min_interest_rate=0.0),
            calculation_timestamp=datetime.now().isoformat(),
            success=False,
            error=error_message
        )

    @staticmethod
    def _validate_input(question_response: QuestionSuccessResponse) -> bool:
        """
        입력 데이터 검증

        Args:
            question_response: QuestionAgent 응답

        Returns:
            bool: 검증 성공 여부
        """
        if not question_response.success:
            print("❌ QuestionAgent 실행이 실패한 상태입니다.")
            return False

        if not question_response.eligible_products:
            print("❌ 적격 상품이 없습니다.")
            return False

        if not question_response.user_conditions:
            print("❌ 사용자 조건이 없습니다.")
            return False

        if not question_response.user_responses:
            print("❌ 사용자 응답이 없습니다.")
            return False

        return True

    def invoke(self, input_data: QuestionSuccessResponse, config=None, **kwargs) -> InterestCalculatorResult:
        """
        Tool 실행 메인 로직 - Runnable 인터페이스

        Args:
            input_data: QuestionAgent 응답
            config: 실행 설정 (선택)

        Returns:
            InterestCalculatorResult: 이자 계산 결과
        """
        print("🔄 InterestCalculatorTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_input(input_data):
            return self._format_error_response("입력 데이터 검증 실패")

        try:
            # 2. 상품 상세 정보 추출
            product_details = self.extract_product_details(input_data.eligible_products)
            if not product_details:
                return self._format_error_response("상품 상세 정보를 가져올 수 없습니다.")

            print(f"📋 {len(product_details)}개 상품 정보 추출 완료")

            # 3. LLM 기반 이자 계산
            calculations = self.calculate_with_llm(product_details, input_data)
            if not calculations:
                return self._format_error_response("이자 계산에 실패했습니다.")

            print(f"💰 {len(calculations)}개 상품 이자 계산 완료")

            # 4. 성공 응답 포맷팅
            return self._format_success_response(calculations, input_data)

        except Exception as e:
            print(f"❌ InterestCalculatorTool 실행 중 오류: {str(e)}")
            return self._format_error_response(f"계산 중 오류 발생: {str(e)}")