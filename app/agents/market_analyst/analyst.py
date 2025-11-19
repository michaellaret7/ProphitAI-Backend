"""Market analyst sub-agent for comprehensive market intelligence and sector analysis.

This module provides a specialized agent that analyzes market sentiment, outlook,
and sector-specific performance using news, macroeconomic data, and price performance.
"""

from datetime import datetime
from typing import Optional

from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.tool_lib.data_tools.news.general_news import GET_GENERAL_NEWS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.news.m_and_a_news import GET_MERGERS_ACQUISITIONS_TOOL
from app.core.agentic_framework.tool_lib.macro_tools.indicators import MACRO_INDICATORS_TOOL
from app.core.agentic_framework.tool_lib.macro_tools.rates import MACRO_RATES_TOOL
from app.core.agentic_framework.tool_lib.macro_tools.commodities import MACRO_COMMODITIES_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.weekly_returns import GET_WEEKLY_RETURNS_TOOL
from app.agents.market_analyst.prompts import MARKET_ANALYST_USER_PROMPT, NEW_MARKET_ANALYST_USER_PROMPT
from app.core.agentic_framework.tool_lib.data_tools.sector_perf import GET_SECTOR_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sector_pe import GET_SECTOR_PE_TOOL

#TODO: This macro analyst agent will be its own agent that will have and run sub agents. The optimizer and builder will use the output of this agent to make their decisions.
# The macro analyst will run ONCE every week to refresh the latest data driven macro backdrop and outlook


class MarketAnalyst(SubAgent):
    """Specialized agent for comprehensive market and sector analysis.

    Provides institutional-grade market intelligence including sentiment analysis,
    forward-looking outlook, sector-by-sector analysis, and ETF type positioning.
    """

    def __init__(self) -> None:
        """Initialize the MarketAnalyst agent.

        Args:
            simulation_date: Optional date for backtesting/simulation mode.
                           If None, uses current date for live analysis.
        """
        super().__init__(
            user_prompt=NEW_MARKET_ANALYST_USER_PROMPT,
            provider="anthropic",
            # model="claude-sonnet-4-5-20250929", 
            model="claude-haiku-4-5-20251001",
            max_iterations=75,
            print_mode=PrintMode.DEBUG,
            temperature=0.5,
            plan_first=True,
            simulation_date=datetime(2023, 1, 1)
        )

        # Reason: Register all tools required for comprehensive market analysis
        tools = [
            GET_GENERAL_NEWS_TOOL,
            GET_MERGERS_ACQUISITIONS_TOOL,
            MACRO_INDICATORS_TOOL,
            MACRO_RATES_TOOL,
            MACRO_COMMODITIES_TOOL,
            GET_WEEKLY_RETURNS_TOOL,
            GET_SECTOR_PERFORMANCE_TOOL,
            GET_SECTOR_PE_TOOL
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )
    
if __name__ == "__main__":
    analyst = MarketAnalyst()
    print(analyst.run())