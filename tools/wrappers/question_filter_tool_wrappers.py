from langchain_core.language_models import BaseLanguageModel

from schemas.question_filter_schema import QuestionFilterToolsWrapper
from tools.condition_extractor import ConditionExtractorTool
from tools.pattern_analyzer import PatternAnalyzerTool


class QuestionFilterTools:
    """QuestionFilterAgent용 Tools 관리 클래스"""

    @staticmethod
    def get_tools(llm: BaseLanguageModel) -> QuestionFilterToolsWrapper:
        """
        QuestionFilterAgent용 Tools 반환

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
        Returns:
            QuestionFilterToolsDict: Tools Wrapper
        """

        tools_dict = {
            "condition_extractor": ConditionExtractorTool(),
            "pattern_analyzer": PatternAnalyzerTool(llm),
        }

        return QuestionFilterToolsWrapper(**tools_dict)
