"""
Tool 2: PatternAnalyzerTool
역할: LLM 기반 우대조건 패턴 분석 및 RAG 쿼리 생성
"""

import json
from langchain.tools import BaseTool
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain_core.language_models import BaseLanguageModel

from prompts.question_prompts import QuestionPrompts
from schemas.question_tool_schema import (
    ConditionExtractorResult,
    PatternAnalysisOutput,
    PatternAnalyzerResult,
)
from langchain_core.runnables import Runnable


class PatternAnalyzerTool(Runnable):
    """
    LLM 기반 우대조건 패턴 분석 및 RAG 쿼리 생성 Tool

    출력: PatternAnalyzerResult
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Tool 초기화

        Args:
            llm: 사용할 llm모델
        """
        super().__init__()
        self.llm = llm

        # Pydantic OutputParser 설정
        self.output_parser = PydanticOutputParser(pydantic_object=PatternAnalysisOutput)

    @staticmethod
    def _extract_analysis_data(
        extracted_conditions: ConditionExtractorResult,
    ) -> dict[str, list[str]]:
        """
        금리정보와 우대조건 텍스트 분리 추출

        Returns:
            dict: 금리정보, 우대조건, 은행명이 분리된 딕셔너리
        """
        rate_info_texts = []
        preferential_texts = []
        bank_names = set()

        for product in extracted_conditions.products:
            bank_names.add(product.product_name.split()[0])  # 은행명 추출

            for chunk in product.chunks:
                formatted_text = f"[{product.product_name}] {chunk.content_natural}"

                if chunk.chunk_type == "basic_rate_info":
                    rate_info_texts.append(formatted_text)
                elif chunk.chunk_type == "preferential_details":
                    preferential_texts.append(formatted_text)

        return {
            "rate_info_texts": rate_info_texts,
            "preferential_texts": preferential_texts,
            "bank_names": list(bank_names),
        }

    @staticmethod
    def _convert_to_schema(llm_output: PatternAnalysisOutput) -> PatternAnalyzerResult:
        """
        LLM 파싱된 출력을 최종 결과 스키마로 변환

        Args:
            llm_output: Pydantic OutputParser로 파싱된 LLM 출력

        Returns:
            PatternAnalyzerResult: 최종 결과 스키마
        """
        try:
            # RAG 쿼리 기본값 추가 (응답이 부족한 경우)
            rag_queries = llm_output.rag_queries
            if not rag_queries:
                rag_queries = [
                    "금리정보 기본금리 우대금리",
                    "우대조건 마케팅 수신 동의",
                    "우대조건 모바일 앱 사용",
                    "우대조건 카드 사용 실적",
                    "파킹통장 금리 조건",
                ]

            result = PatternAnalyzerResult(
                analysis_patterns=llm_output.patterns,
                rag_queries=rag_queries,
                total_patterns=len(llm_output.patterns),
                analysis_success=True,
            )

            return result

        except Exception as e:
            print(f"❌ 스키마 변환 실패: {str(e)}")
            return PatternAnalyzerResult(
                analysis_patterns=[],
                rag_queries=["우대조건 패턴 분석", "금리정보 패턴"],
                total_patterns=0,
                analysis_success=False,
            )

    @staticmethod
    def _validate_input(extracted_conditions: ConditionExtractorResult) -> bool:
        """
        입력 데이터 검증

        Args:
            extracted_conditions: Tool 1의 출력 결과

        Returns:
            bool: 검증 성공 여부
        """
        if not extracted_conditions.success:
            print("❌ ConditionExtractorTool 실행이 실패한 상태입니다.")
            return False

        if not extracted_conditions.products:
            print("❌ 분석할 우대조건 데이터가 없습니다.")
            return False

        return True

    def invoke(
        self, extracted_conditions: ConditionExtractorResult, config=None, **kwargs
    ) -> PatternAnalyzerResult:
        """
        Tool 실행 메인 로직

        Args:
            extracted_conditions: Tool 1의 출력 결과
            config (dict, optional): LangChain 실행 설정. Defaults to None.

        Returns:
            PatternAnalyzerResult: 패턴 분석 결과
        """
        print("🔄 PatternAnalyzerTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_input(extracted_conditions):
            print("❌ 입력 데이터 검증 실패")
            return PatternAnalyzerResult(
                analysis_patterns=[],
                rag_queries=[],
                total_patterns=0,
                analysis_success=False,
            )

        try:
            # 2. 분석 데이터 추출
            analysis_data = self._extract_analysis_data(extracted_conditions)
            print("📝 분석 데이터 추출 완료")

            # 3. 프롬프트 템플릿 생성
            # 프롬프트 인스턴스 생성 및 템플릿 구성
            prompts = QuestionPrompts()
            prompt_text = prompts.pattern_analysis(
                rate_info_texts=analysis_data["rate_info_texts"],
                preferential_texts=analysis_data["preferential_texts"],
                bank_names=analysis_data["bank_names"],
            )

            prompt_template = PromptTemplate(
                template=prompt_text + "\n\n{format_instructions}",
                input_variables=[],
                partial_variables={
                    "format_instructions": self.output_parser.get_format_instructions()
                },
            )
            print(f"prompt_template: {prompt_template.template}")

            # 4. LCEL 체이닝 구성
            chain = (
                RunnablePassthrough()
                | prompt_template
                | self.llm
                | self.output_parser
                | RunnableLambda(self._convert_to_schema)
            )

            print(f"🔎 llm 요청중..")

            # 5. 체인 실행
            result = chain.invoke({})
            print("🤖 LLM 패턴 분석 및 변환 완료")

            if result.analysis_success:
                print(
                    f"✅ PatternAnalyzerTool 실행 완료: {result.total_patterns}개 패턴 분석, {len(result.rag_queries)}개 RAG 쿼리 생성"
                )
                for query in result.rag_queries:
                    print(f"✅ query: {query}")

            else:
                print("⚠️ PatternAnalyzerTool 부분 완료: 기본 RAG 쿼리로 대체")

            return result

        except Exception as e:
            print(f"❌ PatternAnalyzerTool 실행 실패: {str(e)}")
            return PatternAnalyzerResult(
                analysis_patterns=[],
                rag_queries=["우대조건 일반 패턴", "금리정보 일반 패턴"],
                total_patterns=0,
                analysis_success=False,
            )
