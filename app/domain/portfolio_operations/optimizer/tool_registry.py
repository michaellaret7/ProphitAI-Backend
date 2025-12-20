from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL, INDUSTRY_CONCENTRATION_TOOL, VAR_CALCULATOR_TOOL
)
from app.core.agentic_framework.tool_lib.agent_specific_tools.optimizer import GET_USER_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst import SECTOR_ANALYST_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.build_allocations import BUILD_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.macro_tools.outlook import MACRO_OUTLOOK_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_TICKER_INFO_TOOL

def register_optimizer_tools(agent):
    # Get user portfolio tool
    agent.add_tool(**GET_USER_PORTFOLIO_TOOL)

    # Macro outlook tool
    agent.add_tool(**MACRO_OUTLOOK_TOOL)
    
    # Sector Analyst tool
    # agent.add_tool(**SECTOR_ANALYST_TOOL)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
    agent.add_tool(**GET_TICKER_INFO_TOOL)

    # Portfolio construction tools
    agent.add_tool(**CORRELATION_MATRIX_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)
    agent.add_tool(**INDUSTRY_CONCENTRATION_TOOL)
    agent.add_tool(**VAR_CALCULATOR_TOOL)
    agent.add_tool(**BUILD_PORTFOLIO_TOOL)
    agent.add_tool(**EQUITY_SCREENER_TOOL)
    agent.add_tool(**ETF_SCREENER_TOOL)
