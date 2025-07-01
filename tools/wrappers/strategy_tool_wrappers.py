from langchain_core.language_models import BaseLanguageModel

from schemas.strategy_tool_schema import StrategyToolsWrapper
from tools.interest_calculator import InterestCalculatorTool
from tools.strategy_scenario import StrategyScenarioTool


class StrategyTools:
    """StrategyAgent용 Tools 관리 클래스"""

    @staticmethod
    def get_tools(llm: BaseLanguageModel) -> StrategyToolsWrapper:
        """
        StrategyAgent용 Tools 반환

        Args:
            llm: LangChain Chat Model 인스턴스 (ChatOpenAI 등)

        Returns:
            StrategyToolsWrapper: Tools Wrapper
        """

        tools_dict = {
            "interest_calculator": InterestCalculatorTool(llm),
            "strategy_scenario": StrategyScenarioTool(llm),
        }

        return StrategyToolsWrapper(**tools_dict)