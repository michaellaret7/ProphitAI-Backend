from datetime import datetime
from app.core.agentic_framework.base_agent.sub_agent import SubAgent
from typing import Optional
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
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
from app.core.agentic_framework.tool_lib.data_tools.stock_screener import STOCK_SCREENER_TOOL
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
from pydantic import BaseModel

class SectorAnalyst(SubAgent):
    def __init__(self, user_prompt: str = None, sector: str = None, simulation_date: Optional[datetime] = None) -> None:
        super().__init__(
            user_prompt=user_prompt,
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            max_iterations=50,
            print_mode=PrintMode.SUBAGENT,
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
            GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
            GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
            # Stock Screening & Discovery
            STOCK_SCREENER_TOOL,
            GET_GROUP_TICKERS_TOOL,
            # Ticker Analysis Tools - Essential
            CALCULATE_TICKER_FACTORS_TOOL,
            GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
            GET_TICKER_FUNDAMENTAL_DATA_TOOL,
            # Ticker Analysis Tools - Supporting
            GET_STOCK_RATINGS_TOOL,
            GET_PRICE_TARGET_DATA_TOOL,
            GET_ANALYST_ESTIMATES_TOOL,
        ]

        for tool in tools:
            self.add_tool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"]
            )

def run_sector_analyst(sector: str, _simulation_date: Optional[datetime] = None) -> str:
    """Execute sector analysis using the SectorAnalyst subagent."""
    try:
        sector_analyst = SectorAnalyst(
            user_prompt=f"Analyze the performance and valuation of the {sector} sector", 
            sector=sector,
            simulation_date=_simulation_date
        )
        output = sector_analyst.run()
        return success_response(output["final_answer"])
    except Exception as e:
        error_msg = f"Error running sector analyst sub-agent: {str(e)}"
        print(f"⚠️  {error_msg}")
        return error_response(error_msg)
