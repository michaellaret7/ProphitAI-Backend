from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.callbacks.state_callback import StateCallback
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sectors import GET_SECTOR_PERFORMANCE_TOOL, GET_SECTOR_PE_TOOL
from app.core.agentic_framework.tool_lib.data_tools.factors import GET_INDUSTRY_FACTOR_BENCHMARK_TOOL, GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals.ttm_ratios import GET_RATIOS_TTM_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_PRODUCT_SEGMENTATION_TOOL, GET_TICKER_PEERS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info.info import GET_TICKER_INFO_TOOL
from app.domain.ai_watchlist.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from typing import Optional
from .models import WatchlistResponse

class AiWatchlistAgent(BaseAgent):
    def __init__(
        self,
        user_preferences: str,
        provider: str = None,
        model: str = None,
        state_callback: Optional[StateCallback] = None,
    ):
        self.user_preferences = user_preferences
        self.user_prompt = self._build_user_prompt()
        self.response_model = WatchlistResponse

        super().__init__(
            provider=provider,
            model=model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self.user_prompt,
            max_iterations=200,
            plan_first=True,
            print_mode=PrintMode.VERBOSE,
            state_callback=state_callback,
            # temperature=0.7,
        )
    
        tools = [
            #  Screener Tools
            EQUITY_SCREENER_TOOL,
            ETF_SCREENER_TOOL,

            #  Ticker Analysis Tools
            GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
            CALCULATE_TICKER_FACTORS_TOOL,
            GET_TICKER_FUNDAMENTAL_DATA_TOOL,
            GET_RATIOS_TTM_TOOL,
            GET_PRODUCT_SEGMENTATION_TOOL,
            GET_TICKER_PEERS_TOOL,
            GET_TICKER_INFO_TOOL,

            #  Sector Analysis Tools
            GET_SECTOR_PERFORMANCE_TOOL,
            GET_SECTOR_PE_TOOL,
            GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
            GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )
        
    def _build_user_prompt(self) -> str:
        return USER_PROMPT_TEMPLATE.format(user_query=self.user_preferences)


if __name__ == "__main__":
    agent = AiWatchlistAgent(
        provider='openai',
        model='gpt-5.2',
        user_preferences=
        "Build me a watchlist of mining companies that have spent heavy amounts on capital expenditures in the last 5 years(today is 12/9/2025) and are now looking to have their capital expenditures pay off and start turning a profit in the next 1-2 years.\n"
        "I want to see companies that have made these capex investments recently, and in the coming years will start to see the benefits of those investments, NOT companies that have already reaped the benefits of their investments or companies that are just beginning their capex programs."
    ).run(response_format=WatchlistResponse)

    # agent = AiWatchlistAgent(
    #     provider='fireworks',
    #     model='Kimi-K2-instruct',
    #     user_preferences=
    #     "Build me a watchlist of mining companies that have spent heavy amounts on capital expenditures in the last 5 years(today is 12/9/2025) and are now looking to have their capital expenditures pay off and start turning a profit in the next 1-2 years.\n"
    #     "I want to see companies that have made these capex investments recently, and in the coming years will start to see the benefits of those investments, NOT companies that have already reaped the benefits of their investments or companies that are just beginning their capex programs."
    # ).run(response_format=WatchlistResponse)



