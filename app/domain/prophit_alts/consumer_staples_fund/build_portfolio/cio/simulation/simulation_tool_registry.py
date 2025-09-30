"""Tool registry for CIO simulation agent.

This module registers simulation-aware versions of all CIO tools that respect
the September 30, 2024 cutoff date.
"""

from app.core.agentic_framework.tool_lib.agent_specific_tools.cio import (
    GET_ANALYST_PICKS_TOOL, PULL_REST_OF_TICKER_POOL_TOOL
)
from app.core.agentic_framework.tool_lib.data_tools.industry_factors import GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sub_industry_factors import GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
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

from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.simulation_tools import (
    fetch_repository_data_simulation,
    get_fundamental_data_simulation,
    get_ticker_performance_and_risk_simulation,
    CALCULATE_PORTFOLIO_RETURNS_METRICS_SIMULATION_TOOL,
    CORRELATION_MATRIX_SIMULATION_TOOL,
    CALCULATE_PORTFOLIO_PERFORMANCE_SIMULATION_TOOL,
    CALCULATE_PORTFOLIO_BETA_VS_INDEX_SIMULATION_TOOL,
)
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.simulation_tools_extended import (
    CALCULATE_GROUP_PERFORMANCES_SIMULATION_TOOL,
    CALCULATE_TICKER_PERFORMANCES_SIMULATION_TOOL,
    CALCULATE_TICKER_FACTORS_SIMULATION_TOOL,
)

# ==================== Simulation-Specific Tool Schemas ==================== #

# Repository data tool (simulation version)
FETCH_TICKER_REPOSITORY_DATA_SIMULATION_TOOL = {
    "name": "fetch_ticker_repository_data",
    "description": (
        "Fetch auxiliary data for a ticker (SIMULATION MODE - data limited to Sept 30, 2024). "
        "Available data types: 'price_target_news', 'grades_individual', 'grades_summary', "
        "'ratings', 'dividends_series'.\n\n"
        "UNAVAILABLE data types (will return errors): 'analyst_recommendations', 'earnings_transcripts', "
        "'latest_transcript', 'press_releases', 'price_target_summary', 'stock_news'.\n\n"
        "Example: fetch_ticker_repository_data(ticker='AAPL', data_type='ratings')"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Ticker symbol (e.g., 'AAPL').",
            },
            "data_type": {
                "type": "string",
                "description": "Type of data to fetch. Only certain types available as of Sept 2024.",
                "enum": [
                    "price_target_news",
                    "grades_individual",
                    "grades_summary",
                    "ratings",
                    "dividends_series",
                ]
            },
            "limit": {
                "type": "integer",
                "description": "Optional max number of items.",
                "minimum": 1,
                "maximum": 4
            }
        },
        "required": ["ticker", "data_type"],
    },
    "function": fetch_repository_data_simulation,
}

# Fundamental data tool (simulation version)
GET_TICKER_FUNDAMENTAL_DATA_SIMULATION_TOOL = {
    "name": "get_ticker_fundamental_data",
    "description": (
        "Get fundamental financial data for a ticker (SIMULATION MODE - data limited to Sept 30, 2024). "
        "Includes income statements, balance sheets, cash flow statements, and financial ratios.\n\n"
        "Example: get_ticker_fundamental_data(ticker='KO', statement_type='balance_sheet', quarters_back=2)"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "The ticker symbol (e.g., 'AAPL', 'MSFT', 'KO').",
            },
            "statement_type": {
                "type": "string",
                "description": "Type of fundamental data to retrieve.",
                "enum": ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]
            },
            "quarters_back": {
                "type": "integer",
                "description": "Number of quarters of historical data to retrieve. Default is 2.",
                "default": 2
            },
        },
        "required": ["ticker", "statement_type"],
    },
    "function": get_fundamental_data_simulation,
}

# Ticker performance tool (simulation version)
GET_TICKER_PERFORMANCE_AND_RISK_SIMULATION_TOOL = {
    "name": "get_ticker_performance_and_risk",
    "description": (
        "Calculate comprehensive performance and risk metrics for a single ticker over 3 years "
        "(SIMULATION MODE - using data up to Sept 30, 2024). "
        "Returns detailed metrics including Sharpe, Sortino, Treynor, Information Ratio, Alpha, "
        "Omega, Sterling, Burke, Martin ratios, capture ratios, win rates, profit factors, "
        "risk measures (pain index, tail ratio, gain/loss ratio, ulcer index, max drawdown), "
        "and returns across multiple timeframes (3Y, 1Y, 6M, 3M). "
        "CRITICAL: You MUST ALWAYS include the ticker parameter. "
        "Example: get_ticker_performance_and_risk(ticker='AAPL')"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": (
                    "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                    "The ticker symbol to analyze. Must be a valid stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL'). "
                    "The function will automatically fetch 3 years of price and dividend data for analysis (up to Sept 30, 2024)."
                ),
                "pattern": "^[A-Z]{1,5}$",
                "minLength": 1,
                "maxLength": 5
            },
        },
        "required": ["ticker"],
        "additionalProperties": False
    },
    "function": get_ticker_performance_and_risk_simulation,
}


def register_cio_simulation_tools(agent):
    """Register all CIO tools with simulation-aware versions for data fetching.

    Args:
        agent: The CIOSimulationAgent instance to register tools on
    """
    # Data tools (no date dependency - use production versions)
    agent.add_tool(**GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)
    agent.add_tool(**GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)

    # Ticker analytics - simulation version (momentum/volatility factors use price data)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_SIMULATION_TOOL)

    # Data tools - simulation versions
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_SIMULATION_TOOL)
    agent.add_tool(**FETCH_TICKER_REPOSITORY_DATA_SIMULATION_TOOL)

    # Agent-specific tools (these don't need simulation wrapping)
    agent.add_tool(**GET_ANALYST_PICKS_TOOL)

    # Portfolio analytics (ALL simulation versions for data-dependent tools)
    agent.add_tool(**CORRELATION_MATRIX_SIMULATION_TOOL)  # Simulation version
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_SIMULATION_TOOL)  # Simulation version
    agent.add_tool(**CALCULATE_PORTFOLIO_RETURNS_METRICS_SIMULATION_TOOL)  # Simulation version
    agent.add_tool(**CALCULATE_GROUP_PERFORMANCES_SIMULATION_TOOL)  # Simulation version
    agent.add_tool(**CALCULATE_TICKER_PERFORMANCES_SIMULATION_TOOL)  # Simulation version
    agent.add_tool(**CALCULATE_PORTFOLIO_BETA_VS_INDEX_SIMULATION_TOOL)  # Simulation version

    # Pure calculation tools (no date dependency - use production versions)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)
    agent.add_tool(**INDUSTRY_CONCENTRATION_TOOL)
    agent.add_tool(**VAR_CALCULATOR_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)

    # Agent-specific (continued)
    agent.add_tool(**PULL_REST_OF_TICKER_POOL_TOOL)

    # Ticker analytics - simulation version
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_SIMULATION_TOOL)