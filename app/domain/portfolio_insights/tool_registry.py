# Atlas tools
from app.core.atlas.tools.data import (
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    GET_RATIOS_TTM_TOOL,
    GET_TICKER_INFO_TOOL,
    GET_TICKER_PEERS_TOOL,
    EQUITY_SCREENER_TOOL,
    ETF_SCREENER_TOOL,
    GET_SECTOR_PERFORMANCE_TOOL,
)
from app.core.atlas.tools.portfolio import (
    CORRELATION_MATRIX_TOOL,
    GET_USER_PORTFOLIO_TOOL,
)
from app.core.atlas.tools.ticker import (
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
    CALCULATE_TICKER_FACTORS_TOOL,
)
from app.core.atlas.tools.risk import (
    RISK_CONTRIBUTION_TOOL,
    DRAWDOWN_PROFILE_TOOL,
)

def register_portfolio_insights_tools(agent):
    # ------- User portfolio tool -----------
    agent.add_tool(**GET_USER_PORTFOLIO_TOOL)
    agent.add_tool(**CORRELATION_MATRIX_TOOL)

    # ------- Risk analysis tools -----------
    agent.add_tool(**RISK_CONTRIBUTION_TOOL)
    agent.add_tool(**DRAWDOWN_PROFILE_TOOL)

    # ------- Sector tools -----------
    agent.add_tool(**GET_SECTOR_PERFORMANCE_TOOL)

    # ------- Ticker tools -----------
    agent.add_tool(**GET_TICKER_INFO_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)
    agent.add_tool(**GET_TICKER_PEERS_TOOL)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
    agent.add_tool(**GET_RATIOS_TTM_TOOL)

    # ------- Screener tools -----------
    agent.add_tool(**EQUITY_SCREENER_TOOL)
    agent.add_tool(**ETF_SCREENER_TOOL)

