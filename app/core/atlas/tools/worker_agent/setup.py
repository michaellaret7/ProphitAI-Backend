"""Worker tool setup - available tools registry and schema constants."""

from typing import Dict, Any, List

from app.core.atlas.tools.responses import error_response

# --- data / etf ---
from app.core.atlas.tools.data.etf.holdings import GET_ETF_HOLDINGS_TOOL
from app.core.atlas.tools.data.etf.info import GET_ETF_INFO_TOOL

# --- data / factors ---
from app.core.atlas.tools.data.factors.industry import GET_INDUSTRY_FACTOR_BENCHMARK_TOOL
from app.core.atlas.tools.data.factors.sub_industry import GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL

# --- data / fundamentals / ticker_info ---
from app.core.atlas.tools.data.fundamentals.ticker_info.info import GET_TICKER_INFO_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_info.peers import GET_TICKER_PEERS_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_info.price_target import GET_PRICE_TARGET_DATA_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_info.product_segmentation import GET_PRODUCT_SEGMENTATION_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_info.ratings import GET_STOCK_RATINGS_TOOL

# --- data / fundamentals / ticker_fundamentals ---
from app.core.atlas.tools.data.fundamentals.ticker_fundamentals.estimates import GET_ANALYST_ESTIMATES_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_fundamentals.statements import GET_TICKER_FUNDAMENTAL_DATA_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_fundamentals.ttm_ratios import GET_RATIOS_TTM_TOOL

# --- data / news ---
from app.core.atlas.tools.data.news.general_news import GET_GENERAL_NEWS_TOOL
from app.core.atlas.tools.data.news.m_and_a_news import GET_MERGERS_ACQUISITIONS_TOOL
from app.core.atlas.tools.data.news.press_releases import GET_PRESS_RELEASES_TOOL
from app.core.atlas.tools.data.news.price_target_news import GET_PRICE_TARGET_NEWS_TOOL
from app.core.atlas.tools.data.news.ticker_news import GET_TICKER_NEWS_TOOL

# --- data / screening ---
from app.core.atlas.tools.data.screening.equity_screener import EQUITY_SCREENER_TOOL
from app.core.atlas.tools.data.screening.etf_screener import ETF_SCREENER_TOOL

# --- data / sectors ---
from app.core.atlas.tools.data.sectors.hierarchy import GET_GROUP_TICKERS_TOOL, GET_SECTOR_INDUSTRIES_TOOL
from app.core.atlas.tools.data.sectors.pe_ratios import GET_SECTOR_PE_TOOL
from app.core.atlas.tools.data.sectors.performance import GET_SECTOR_PERFORMANCE_TOOL

# --- foundry tools ---
from app.core.atlas.tools.foundry.credit_research import CREDIT_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.tools.foundry.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.tax_research import TAX_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.user_uploads import USER_UPLOAD_SEARCH_TOOL

# --- macro tools ---
from app.core.atlas.tools.macro.commodities import MACRO_COMMODITIES_TOOL
from app.core.atlas.tools.macro.indicators import MACRO_INDICATORS_TOOL
from app.core.atlas.tools.macro.outlook import MACRO_OUTLOOK_TOOL
from app.core.atlas.tools.macro.rates import MACRO_RATES_TOOL

# --- portfolio tools ---
from app.core.atlas.tools.portfolio.beta import CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL
from app.core.atlas.tools.portfolio.build_allocations import BUILD_PORTFOLIO_TOOL
from app.core.atlas.tools.portfolio.concentration import (
    EXPOSURE_CALCULATOR_TOOL,
    INDUSTRY_CONCENTRATION_TOOL,
    VAR_CALCULATOR_TOOL,
)
from app.core.atlas.tools.portfolio.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.atlas.tools.portfolio.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.atlas.tools.portfolio.get_user_portfolio import GET_USER_PORTFOLIO_TOOL
from app.core.atlas.tools.portfolio.group_performance import CALCULATE_GROUP_PERFORMANCES_TOOL
from app.core.atlas.tools.portfolio.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.atlas.tools.portfolio.returns import CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL
from app.core.atlas.tools.portfolio.ticker_performance import CALCULATE_TICKER_PERFORMANCES_TOOL

# --- risk tools ---
from app.core.atlas.tools.risk.asset_risk_contrib import RISK_CONTRIBUTION_TOOL
from app.core.atlas.tools.risk.cov_matrix import CALCULATE_COVARIANCE_MATRIX_TOOL
from app.core.atlas.tools.risk.drawdown_profile import DRAWDOWN_PROFILE_TOOL
from app.core.atlas.tools.risk.pairwise_corr_analysis import PAIRWISE_CORR_ANALYSIS_TOOL
from app.core.atlas.tools.risk.stress_test import STRESS_TEST_TOOL
from app.core.atlas.tools.risk.vol_es import VOL_ES_TOOL

# --- ticker tools ---
from app.core.atlas.tools.ticker.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.atlas.tools.ticker.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.atlas.tools.ticker.technicals import TECHNICALS_TOOL
from app.core.atlas.tools.ticker.weekly_returns import GET_WEEKLY_RETURNS_TOOL

# ==============================================================================
# AVAILABLE TOOLS — name → TOOL dict lookup
# ==============================================================================

AVAILABLE_TOOLS: Dict[str, Dict[str, Any]] = {
    # data / etf
    "get_etf_holdings": GET_ETF_HOLDINGS_TOOL,
    "get_etf_info": GET_ETF_INFO_TOOL,
    # data / factors
    "get_industry_factor_benchmark": GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
    "get_sub_industry_factor_benchmark": GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
    # data / fundamentals / ticker_info
    "get_ticker_info": GET_TICKER_INFO_TOOL,
    "get_ticker_peers": GET_TICKER_PEERS_TOOL,
    "get_price_target_data": GET_PRICE_TARGET_DATA_TOOL,
    "get_product_segmentation": GET_PRODUCT_SEGMENTATION_TOOL,
    "get_stock_ratings": GET_STOCK_RATINGS_TOOL,
    # data / fundamentals / ticker_fundamentals
    "get_analyst_estimates": GET_ANALYST_ESTIMATES_TOOL,
    "get_ticker_fundamental_data": GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    "get_ratios_ttm": GET_RATIOS_TTM_TOOL,
    # data / news
    "get_general_news": GET_GENERAL_NEWS_TOOL,
    "get_mergers_acquisitions": GET_MERGERS_ACQUISITIONS_TOOL,
    "get_press_releases": GET_PRESS_RELEASES_TOOL,
    "get_price_target_news": GET_PRICE_TARGET_NEWS_TOOL,
    "get_ticker_news": GET_TICKER_NEWS_TOOL,
    # data / screening
    "equity_screener": EQUITY_SCREENER_TOOL,
    "etf_screener": ETF_SCREENER_TOOL,
    # data / sectors
    "get_group_tickers": GET_GROUP_TICKERS_TOOL,
    "get_sector_industries": GET_SECTOR_INDUSTRIES_TOOL,
    "get_sector_pe": GET_SECTOR_PE_TOOL,
    "get_sector_performance": GET_SECTOR_PERFORMANCE_TOOL,
    # foundry
    "credit_research_search": CREDIT_RESEARCH_SEARCH_TOOL,
    "earnings_call_search": EARNINGS_CALL_SEARCH_TOOL,
    "macro_research_search": MACRO_RESEARCH_SEARCH_TOOL,
    "tax_research_search": TAX_RESEARCH_SEARCH_TOOL,
    "user_upload_search": USER_UPLOAD_SEARCH_TOOL,
    # macro
    "macro_commodities": MACRO_COMMODITIES_TOOL,
    "macro_indicators": MACRO_INDICATORS_TOOL,
    "macro_outlook": MACRO_OUTLOOK_TOOL,
    "macro_rates": MACRO_RATES_TOOL,
    # portfolio
    "build_portfolio_allocations": BUILD_PORTFOLIO_TOOL,
    "calculate_portfolio_beta_vs_index": CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
    "portfolio_exposure_calculator": EXPOSURE_CALCULATOR_TOOL,
    "portfolio_industry_concentration": INDUSTRY_CONCENTRATION_TOOL,
    "portfolio_VaR_calculator": VAR_CALCULATOR_TOOL,
    "calculate_portfolio_correlation_matrix": CORRELATION_MATRIX_TOOL,
    "calculate_portfolio_factor_tilts": FACTOR_TILTS_FOR_PORTFOLIO_TOOL,
    "get_user_portfolio": GET_USER_PORTFOLIO_TOOL,
    "calculate_group_performances": CALCULATE_GROUP_PERFORMANCES_TOOL,
    "calculate_portfolio_performance": CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
    "calculate_portfolio_returns_metrics": CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
    "calculate_ticker_performances": CALCULATE_TICKER_PERFORMANCES_TOOL,
    # risk
    "portfolio_risk_contribution_by_asset": RISK_CONTRIBUTION_TOOL,
    "portfolio_covariance_matrix": CALCULATE_COVARIANCE_MATRIX_TOOL,
    "portfolio_drawdown_profile": DRAWDOWN_PROFILE_TOOL,
    "portfolio_pairwise_correlation_analysis": PAIRWISE_CORR_ANALYSIS_TOOL,
    "portfolio_stress_test": STRESS_TEST_TOOL,
    "portfolio_vol_es": VOL_ES_TOOL,
    # ticker
    "calculate_ticker_factors": CALCULATE_TICKER_FACTORS_TOOL,
    "get_ticker_performance_and_risk": GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
    "run_technicals": TECHNICALS_TOOL,
    "get_weekly_returns": GET_WEEKLY_RETURNS_TOOL,
}


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

DEPLOY_WORKER_DESCRIPTION = (
    "Deploy a focused worker agent to autonomously execute a specific sub-task. "
    "The worker runs its own tool-calling loop with the tools you select and returns "
    "a structured result.\n\n"
    "**WHEN TO USE:**\n"
    "- Research tasks: earnings call analysis, news summarization, sector deep-dives\n"
    "- Data-heavy analysis that requires multiple sequential tool calls\n"
    "- Any focused sub-task that benefits from isolated execution\n\n"
    "**HOW IT WORKS:**\n"
    "1. Provide a clear, detailed task description\n"
    "2. Select the tools the worker needs from the available set\n"
    "3. The worker agent executes autonomously and returns results\n\n"
    "**TIPS FOR GOOD TASK DESCRIPTIONS:**\n"
    "- Be specific about what data to gather and what output format you expect\n"
    "- Include relevant context (tickers, time periods, metrics of interest)\n"
    "- State the end goal clearly so the worker knows when it's done\n\n"
    "Example: deploy_worker_agent(\n"
    "  task='Research the latest earnings call for AAPL. Summarize key metrics, "
    "management guidance, and notable analyst Q&A.',\n"
    "  tools=['earnings_call_search', 'get_ticker_news']\n"
    ")"
)

DEPLOY_WORKER_PARAMETERS = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": (
                "A clear, detailed description of the task for the worker agent. "
                "Include all relevant context: tickers, time periods, metrics, "
                "and desired output format."
            )
        },
        "tools": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": sorted(AVAILABLE_TOOLS.keys()),
            },
            "description": "List of tool names to equip the worker agent with.",
            "minItems": 1
        }
    },
    "required": ["task", "tools"],
    "additionalProperties": False
}

# Reason: WorkerAgent auto-registers these via AgentBase and its own __init__,
# so the orchestrator may redundantly request them. Skip silently.
_WORKER_DEFAULT_TOOLS = {"think", "calculator", "llm_web_search", "write_note"}


def _resolve_and_deploy(task: str, tools: List[str]) -> str:
    """Resolve tool name strings to tool dicts, then deploy the worker agent."""
    from app.core.atlas.tools.worker_agent.worker import deploy_worker_agent

    tool_defs = []
    for name in tools:
        if name in _WORKER_DEFAULT_TOOLS:
            continue
        tool = AVAILABLE_TOOLS.get(name)
        if tool is None:
            return error_response(
                f"Unknown tool '{name}'. Available: {sorted(AVAILABLE_TOOLS.keys())}"
            )
        tool_defs.append(tool)

    return deploy_worker_agent(task=task, tools=tool_defs)


DEPLOY_WORKER_TOOL = {
    "name": "deploy_worker_agent",
    "description": DEPLOY_WORKER_DESCRIPTION,
    "parameters": DEPLOY_WORKER_PARAMETERS,
    "function": _resolve_and_deploy,
}
