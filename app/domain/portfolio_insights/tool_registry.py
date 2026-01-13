from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_TICKER_INFO_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_TICKER_PEERS_TOOL
from app.core.agentic_framework.tool_lib.agent_specific_tools.optimizer import GET_USER_PORTFOLIO_TOOL

def register_portfolio_insights_tools(agent):
    agent.add_tool(**GET_USER_PORTFOLIO_TOOL)
    agent.add_tool(**CORRELATION_MATRIX_TOOL)

    # ------- Ticker tools -----------
    agent.add_tool(**GET_TICKER_INFO_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)
    agent.add_tool(**GET_TICKER_PEERS_TOOL)