"""
QuestionFilterAgent용 LangChain Tool Wrapper 클래스들
기존 Tool들을 LangChain BaseTool 표준 방식으로 래핑
"""

from langchain.tools import BaseTool
from langchain.llms.base import LLM

from tools.condition_extractor import ConditionExtractorTool
from tools.pattern_analyzer import PatternAnalyzerTool

from schemas.agent_responses import EligibilitySuccessResponse
from schemas.question_filter_schema import ConditionExtractorResult, PatternAnalyzerResult


class ConditionExtractorToolWrapper(BaseTool):
    """
    ConditionExtractorTool의 LangChain BaseTool 래퍼

    기존 Tool을 LangChain 표준 방식으로 사용 가능하게 래핑
    """

    name: str = "condition_extractor_wrapper"
    description: str = "Extracts preferential condition and rate information chunk data from MongoDB based on product codes from eligible products."

    def _run(self, eligibility_response: EligibilitySuccessResponse) -> ConditionExtractorResult:
        """
        Tool 실행

        Args:
            eligibility_response: EligibilityAgent 응답

        Returns:
            ConditionExtractorResult: 우대조건 청크 추출 결과
        """
        extractor = ConditionExtractorTool(eligibility_response)
        return extractor._run()


class PatternAnalyzerToolWrapper(BaseTool):
    """
    PatternAnalyzerTool의 LangChain BaseTool 래퍼

    LLM을 주입받아 패턴 분석을 수행하는 Tool 래퍼
    """

    name: str = "pattern_analyzer_wrapper"
    description: str = "Analyzes rate information and preferential condition patterns using LLM and generates RAG queries for question generation."

    def __init__(self, llm: LLM):
        """
        Tool 래퍼 초기화

        Args:
            llm: LangChain LLM 인스턴스
        """
        super().__init__()
        self.llm = llm

    def _run(self, extractor_result: ConditionExtractorResult) -> PatternAnalyzerResult:
        """
        Tool 실행

        Args:
            extractor_result: ConditionExtractorTool 실행 결과

        Returns:
            PatternAnalysisResult: 패턴 분석 결과
        """
        analyzer = PatternAnalyzerTool(self.llm, extractor_result)
        return analyzer._run()