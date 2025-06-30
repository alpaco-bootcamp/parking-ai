from langchain_core.language_models import BaseLanguageModel

from schemas.question_schema import QuestionToolsWrapper
from tools.condition_extractor import ConditionExtractorTool
from tools.pattern_analyzer import PatternAnalyzerTool
from tools.question_generator import QuestionGeneratorTool
from tools.user_input import UserInputTool


class QuestionTools:
    """QuestionAgent용 Tools 관리 클래스"""

    @staticmethod
    def get_tools(llm: BaseLanguageModel, test_mode: bool = True) -> QuestionToolsWrapper:
        """
        QuestionAgent용 Tools 반환

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)
            test_mode: 테스트 모드 여부 (UserInputTool에서 사용)
        Returns:
            QuestionToolsDict: Tools Wrapper
        """

        tools_dict = {
            "condition_extractor": ConditionExtractorTool(),
            "pattern_analyzer": PatternAnalyzerTool(llm),
            "question_generator": QuestionGeneratorTool(llm),
            "user_input": UserInputTool(test_mode),
        }

        return QuestionToolsWrapper(**tools_dict)
