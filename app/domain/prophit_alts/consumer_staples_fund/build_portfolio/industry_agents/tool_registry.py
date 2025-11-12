from app.core.agentic_framework.tool_lib.agent_specific_tools.industry import (
    GET_ELIGIBLE_TICKERS_TOOL,
    GET_BASE_TICKER_INFO_TOOL
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_repository import FETCH_TICKER_REPOSITORY_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.industry_factors import GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sub_industry_factors import GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.weekly_returns import GET_WEEKLY_RETURNS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL

def register_industry_tools(agent):
    agent.add_tool(**GET_ELIGIBLE_TICKERS_TOOL)
    agent.add_tool(**GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)
    agent.add_tool(**GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
    agent.add_tool(**FETCH_TICKER_REPOSITORY_DATA_TOOL)
    agent.add_tool(**GET_BASE_TICKER_INFO_TOOL)
    agent.add_tool(**GET_WEEKLY_RETURNS_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)