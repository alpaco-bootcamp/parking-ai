"""
Tool 3: QuestionGeneratorTool
역할: 패턴 분석 결과 기반으로 RAG 검색하여 사용자 질문 생성
"""

from langchain.schema.runnable import Runnable
from langchain.llms.base import LLM
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain_core.language_models import BaseLanguageModel

from rag.retriever import ParkingRetriever
from prompts.question_prompts import QuestionPrompts
from schemas.question_schema import (
    QuestionGeneratorResult,
    UserQuestion,
    PATTERN_TO_CATEGORY_MAP,
)
from schemas.question_schema import PatternAnalyzerResult


class QuestionGeneratorTool(Runnable):
    """
    패턴 분석 결과를 기반으로 RAG 검색하여 사용자 질문을 생성하는 Tool

    입력: PatternAnalyzerResult
    출력: QuestionGeneratorResult
    """

    def __init__(self, llm: BaseLanguageModel):
        """
        Tool 초기화

        Args:
            llm: 사용할 llm모델
        """
        super().__init__()
        self.llm = llm
        self.retriever = ParkingRetriever()

        # PydanticOutputParser 설정 - QuestionGeneratorResult 직접 사용
        self.output_parser = PydanticOutputParser(
            pydantic_object=QuestionGeneratorResult
        )

    def perform_rag_search(self, rag_queries: list[str]) -> str:
        """
        RAG 쿼리를 사용하여 벡터 검색 수행하고 컨텍스트 문자열로 반환

        Args:
            rag_queries: RAG 검색 쿼리 목록 (우대조건 첫 거래 고객 우대, 우대조건 자동이체 실적)

        Returns:
            str: RAG 검색 결과를 문자열로 포맷팅한 컨텍스트
        """
        context_parts = []

        for query in rag_queries:
            try:
                # chunks 벡터스토어 사용하여 검색 (k=10으로 제한)
                self.retriever.load_vector_stores()
                docs_with_scores = (
                    self.retriever.chunks_vector_store.similarity_search_with_score(
                        query, k=10
                    )
                )

                for doc, score in docs_with_scores:
                    product_name = doc.metadata.get("product_name", "Unknown")
                    content = doc.page_content
                    print(f"⭐️RAG Score: {score}")
                    print(f"⭐️RAG content: {content}")

                    context_parts.append(
                        f"[{product_name}] {content} (유사도: {score:.2f})"
                    )

            except Exception as e:
                print(f"⚠️ RAG 검색 실패 (쿼리: {query}): {str(e)}")
                continue

        # 최대 30개 결과만 사용
        if len(context_parts) > 30:
            context_parts = context_parts[:30]

        return (
            "\n".join(context_parts)
            if context_parts
            else "검색된 우대조건 사례가 없습니다."
        )

    @staticmethod
    def _convert_to_schema(
        llm_output: QuestionGeneratorResult,
    ) -> QuestionGeneratorResult:
        """
        LLM 파싱된 출력을 최종 결과 스키마로 변환 및 category 매핑

        Args:
            llm_output: Pydantic OutputParser로 파싱된 LLM 출력

        Returns:
            QuestionGeneratorResult: 최종 결과 스키마
        """
        try:
            # category 매핑 처리
            converted_questions = []

            for question in llm_output.questions:
                # 패턴명을 영문 카테고리로 매핑
                pattern_name = question.category  # LLM이 생성한 패턴명
                english_category = PATTERN_TO_CATEGORY_MAP.get(pattern_name, "online")

                converted_question = UserQuestion(
                    id=question.id,
                    category=english_category,
                    question=question.question,
                    impact=question.impact,
                )
                converted_questions.append(converted_question)

            result = QuestionGeneratorResult(
                questions=converted_questions,
                total_questions=len(converted_questions),
                estimated_time=llm_output.estimated_time,
                generation_success=True,
            )

            return result

        except Exception as e:
            print(f"❌ 스키마 변환 실패: {str(e)}")
            return QuestionGeneratorResult(
                questions=[],
                total_questions=0,
                estimated_time="0분",
                generation_success=False,
            )

    @staticmethod
    def _validate_input(pattern_analyzer_result: PatternAnalyzerResult) -> bool:
        """
        입력 데이터 검증

        Args:
            pattern_analyzer_result: Tool 2의 출력 결과

        Returns:
            bool: 검증 성공 여부
        """
        if not pattern_analyzer_result.analysis_success:
            print("❌ PatternAnalyzerTool 실행이 실패한 상태입니다.")
            return False

        if not pattern_analyzer_result.rag_queries:
            print("❌ RAG 쿼리가 없습니다.")
            return False

        return True

    def invoke(
        self, input_data: PatternAnalyzerResult, config=None, **kwargs
    ) -> QuestionGeneratorResult:
        """
        Runnable 인터페이스 구현

        Args:
            input_data: Tool2의 출력결과(PatternAnalyzerResult)
            config: 실행 설정 (사용되지 않음)

        Returns:
            QuestionGeneratorResult: 질문 생성 결과
        """
        print("🔄 QuestionGeneratorTool 실행 시작")

        # 1. 입력 데이터 검증
        if not self._validate_input(input_data):
            print("❌ 입력 데이터 검증 실패")
            return QuestionGeneratorResult(
                questions=[],
                total_questions=0,
                estimated_time="0분",
                generation_success=False,
            )

        try:
            # 2. RAG 검색 수행하여 컨텍스트 생성
            print("🔍 RAG 검색 수행 중...")
            rag_context = self.perform_rag_search(input_data.rag_queries)
            print(f"📊 RAG 검색 완료")

            # 3. input_data affected_banks 정보 추출
            affected_banks = []
            if input_data.analysis_patterns:
                for pattern in input_data.analysis_patterns:
                    if pattern.affected_banks:
                        affected_banks.extend(pattern.affected_banks)

                # 중복 제거하고 정렬
                affected_banks = sorted(list(set(affected_banks)))

            # 4. 우대조건 패턴만 추출
            preferential_patterns = [
                pattern
                for pattern in input_data.analysis_patterns
                if pattern.pattern_type == "preferential_condition"
            ]

            # 5. 프롬프트 템플릿 생성
            prompts = QuestionPrompts()
            prompt_text = prompts.question_generation_with_rag(
                preferential_patterns=preferential_patterns,
                rag_context=rag_context,
                affected_banks=affected_banks,
            )

            prompt_template = PromptTemplate(
                template=prompt_text + "\n\n{format_instructions}",
                input_variables=[],
                partial_variables={
                    "format_instructions": self.output_parser.get_format_instructions()
                },
            )

            print("🤖 LLM 질문 중..")
            print(prompt_template.template)

            # 5. LCEL 체이닝 구성
            chain = (
                RunnablePassthrough()
                | prompt_template
                | self.llm
                | self.output_parser
                | RunnableLambda(self._convert_to_schema)
            )

            # 6. 체인 실행
            result = chain.invoke({})
            print("🤖 LLM 질문 생성 및 변환 완료")

            if result.generation_success:
                print(
                    f"✅ QuestionGeneratorTool 실행 완료: {result.total_questions}개 질문 생성"
                )
            else:
                print("⚠️ QuestionGeneratorTool 부분 완료: 기본 질문으로 대체")

            return result

        except Exception as e:
            print(f"❌ QuestionGeneratorTool 실행 실패: {str(e)}")
            return QuestionGeneratorResult(
                questions=[],
                total_questions=0,
                estimated_time="0분",
                generation_success=False,
            )
