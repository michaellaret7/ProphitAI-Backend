# Atlas tools
from app.core.atlas.tools.portfolio import (
    CORRELATION_MATRIX_TOOL,
    CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
    FACTOR_TILTS_FOR_PORTFOLIO_TOOL,
    EXPOSURE_CALCULATOR_TOOL,
    INDUSTRY_CONCENTRATION_TOOL,
    VAR_CALCULATOR_TOOL,
    BUILD_PORTFOLIO_TOOL,
    GET_USER_PORTFOLIO_TOOL,
)
from app.core.atlas.tools.macro import MACRO_OUTLOOK_TOOL
from app.core.atlas.tools.data import (
    EQUITY_SCREENER_TOOL,
    ETF_SCREENER_TOOL,
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    GET_TICKER_INFO_TOOL,
)
from app.core.atlas.tools.ticker import (
    CALCULATE_TICKER_FACTORS_TOOL,
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
)
from app.core.atlas.tools.portfolio.get_user_portfolio import GET_USER_PORTFOLIO_TOOL


def register_optimizer_tools(agent):
    # Get user portfolio tool
    agent.add_tool(**GET_USER_PORTFOLIO_TOOL)

    # Macro outlook tool
    agent.add_tool(**MACRO_OUTLOOK_TOOL)
    
    # Ticker tools
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

    # Screener tools
    agent.add_tool(**EQUITY_SCREENER_TOOL)
    agent.add_tool(**ETF_SCREENER_TOOL)
