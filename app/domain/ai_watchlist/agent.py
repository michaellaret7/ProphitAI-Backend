from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.base_agent.callbacks import StateCallback
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
    def __init__(self, user_preferences: str, state_callback: Optional["StateCallback"] = None):
        self.user_preferences = user_preferences
        self.user_prompt = self._build_user_prompt()
        
        super().__init__(
            # provider="deepseek",
            # model="deepseek-chat",
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self.user_prompt,
            max_iterations=80,
            plan_first=True,
            print_mode=PrintMode.DEBUG,
            state_callback=state_callback,
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
    import time
    start_time = time.time()
    agent = AiWatchlistAgent(
        user_preferences="Build me a watchlist of 5-10 tickers in the Airlines/Aviation field that are very value/quality driven with strong growth outlook. "
    )
    print(agent)
    result = agent.run(response_format=WatchlistResponse)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.4f} seconds")

    if result.get("parsed_output"):
        print(result["parsed_output"].model_dump_json(indent=2))
    else:
        print("Raw answer:", result["final_answer"])


