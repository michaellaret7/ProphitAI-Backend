from app.core.agentic_framework.tool_lib.agent_specific_tools.cio import (
    GET_ANALYST_PICKS_TOOL, PULL_REST_OF_TICKER_POOL_TOOL
)
from app.core.agentic_framework.tool_lib.data_tools.industry_factors import GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sub_industry_factors import GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.repository import FETCH_TICKER_REPOSITORY_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.stock_screener import STOCK_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.group_performance import CALCULATE_GROUP_PERFORMANCES_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.ticker_performance import CALCULATE_TICKER_PERFORMANCES_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.build_allocations import BUILD_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.beta import CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL, INDUSTRY_CONCENTRATION_TOOL, VAR_CALCULATOR_TOOL
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL

def register_cio_tools(agent):
    # Data tools
    agent.add_tool(**GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)
    agent.add_tool(**GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)

    # Ticker analytics
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)

    # Data tools (continued)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
    agent.add_tool(**FETCH_TICKER_REPOSITORY_DATA_TOOL)
    agent.add_tool(**STOCK_SCREENER_TOOL)

    # Agent-specific
    agent.add_tool(**GET_ANALYST_PICKS_TOOL)

    # Portfolio analytics
    agent.add_tool(**CORRELATION_MATRIX_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL)
    agent.add_tool(**CALCULATE_GROUP_PERFORMANCES_TOOL)
    agent.add_tool(**CALCULATE_TICKER_PERFORMANCES_TOOL)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)
    agent.add_tool(**INDUSTRY_CONCENTRATION_TOOL)
    agent.add_tool(**VAR_CALCULATOR_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)

    # Portfolio construction
    agent.add_tool(**BUILD_PORTFOLIO_TOOL)

    # Agent-specific (continued)
    agent.add_tool(**PULL_REST_OF_TICKER_POOL_TOOL)

    # Ticker analytics
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)