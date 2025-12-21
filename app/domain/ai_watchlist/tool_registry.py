from app.core.agentic_framework.tool_lib.data_tools.screeners.equity_screener import EQUITY_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf_screener import ETF_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sectors import GET_SECTOR_PERFORMANCE_TOOL, GET_SECTOR_PE_TOOL
from app.core.agentic_framework.tool_lib.data_tools.factors import GET_INDUSTRY_FACTOR_BENCHMARK_TOOL, GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals.ttm_ratios import GET_RATIOS_TTM_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info import GET_PRODUCT_SEGMENTATION_TOOL, GET_TICKER_PEERS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_info.info import GET_TICKER_INFO_TOOL

def register_ai_watchlist_tools(agent):
    agent.add_tool(**EQUITY_SCREENER_TOOL)
    agent.add_tool(**ETF_SCREENER_TOOL)
    agent.add_tool(**GET_SECTOR_PERFORMANCE_TOOL)
    agent.add_tool(**GET_SECTOR_PE_TOOL)
    agent.add_tool(**GET_INDUSTRY_FACTOR_BENCHMARK_TOOL)
    agent.add_tool(**GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_TOOL)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
    agent.add_tool(**GET_RATIOS_TTM_TOOL)
    agent.add_tool(**GET_PRODUCT_SEGMENTATION_TOOL)
    agent.add_tool(**GET_TICKER_PEERS_TOOL)
    agent.add_tool(**GET_TICKER_INFO_TOOL)