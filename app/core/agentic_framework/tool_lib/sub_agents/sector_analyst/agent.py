from datetime import datetime
from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from typing import Optional
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.tool_lib.data_tools.sectors import (
    GET_SECTOR_PERFORMANCE_TOOL,
    GET_SECTOR_PE_TOOL,
    GET_SECTOR_INDUSTRIES_TOOL,
    GET_GROUP_TICKERS_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.factors import (
    GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
    GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import (
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    GET_ANALYST_ESTIMATES_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import (
    GET_STOCK_RATINGS_TOOL,
    GET_PRICE_TARGET_DATA_TOOL,
)
from app.core.agentic_framework.tool_lib.data_tools.etf.holdings import GET_ETF_HOLDINGS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.etf.info import GET_ETF_INFO_TOOL
from app.core.agentic_framework.tool_lib.data_tools.news.ticker_news import GET_TICKER_NEWS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals.ttm_ratios import GET_RATIOS_TTM_TOOL

class SectorAnalyst(SubAgent):
    def __init__(self, user_prompt: str = None, sector: str = None, simulation_date: Optional[datetime] = None) -> None:
        super().__init__(
            user_prompt=user_prompt,
            provider="grok",
            model="grok-4-1-fast-reasoning",
            max_iterations=80,
            print_mode=PrintMode.VERBOSE,
            temperature=0.7,
            plan_first=True,
            simulation_date=simulation_date
        )

        tools = [
            # Sector-Level Analysis
            GET_SECTOR_PERFORMANCE_TOOL,
            GET_SECTOR_PE_TOOL,
            GET_SECTOR_INDUSTRIES_TOOL,
            # Industry/Sub-Industry Benchmarking
            # GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
            GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
            # Stock Screening & Discovery
            EQUITY_SCREENER_TOOL,
            ETF_SCREENER_TOOL,
            GET_GROUP_TICKERS_TOOL,
            GET_ETF_HOLDINGS_TOOL,
            GET_ETF_INFO_TOOL,
            # Ticker Analysis Tools - Essential
            CALCULATE_TICKER_FACTORS_TOOL,
            GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
            GET_TICKER_FUNDAMENTAL_DATA_TOOL,
            # Ticker Analysis Tools - Supporting
            GET_STOCK_RATINGS_TOOL,
            GET_PRICE_TARGET_DATA_TOOL,
            GET_ANALYST_ESTIMATES_TOOL,
            GET_RATIOS_TTM_TOOL,
            GET_TICKER_NEWS_TOOL,
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )
