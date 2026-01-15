from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals.statements import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals.ttm_ratios import GET_RATIOS_TTM_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.agent_specific_tools.optimizer import GET_USER_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_TICKER_INFO_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_TICKER_PEERS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.asset_risk_contrib import RISK_CONTRIBUTION_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.drawdown_profile import DRAWDOWN_PROFILE_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sectors.performance import GET_SECTOR_PERFORMANCE_TOOL

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

