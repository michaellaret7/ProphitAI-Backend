"""Centralized Tool Registry - Single source of truth for all agent tool functions and categories.

Both the ChatAgent (via register_tools) and WorkerAgent (via setup.py) consume
this registry, eliminating duplicated import lists.
"""

from typing import Any, Callable, Dict, List, Set

# ================================
# --> Imports: ticker analytics
# ================================
from app.core.atlas.tools.ticker.performance import ticker_performance
from app.core.atlas.tools.ticker.risk import ticker_risk
from app.core.atlas.tools.ticker.factors import ticker_factors
from app.core.atlas.tools.ticker.technicals import ticker_technicals

# ================================
# --> Imports: ticker info
# ================================
from app.core.atlas.tools.ticker.info.description import get_ticker_info, get_etf_info
from app.core.atlas.tools.ticker.info.peers import get_ticker_peers
from app.core.atlas.tools.ticker.info.ratings import get_stock_ratings
from app.core.atlas.tools.ticker.info.institutional_holders import get_institutional_holders
from app.core.atlas.tools.ticker.info.product_segmentation import get_product_segmentation
from app.core.atlas.tools.ticker.info.etf_holdings import get_etf_holdings

# ================================
# --> Imports: sectors
# ================================
from app.core.atlas.tools.ticker.info.sectors import get_sector_industries, get_group_tickers

# ================================
# --> Imports: fundamentals
# ================================
from app.core.atlas.tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from app.core.atlas.tools.ticker.fundamentals.price_target import get_price_target_data

# ================================
# --> Imports: portfolio
# ================================
from app.core.atlas.tools.portfolio.performance import portfolio_performance
from app.core.atlas.tools.portfolio.risk import portfolio_risk
from app.core.atlas.tools.portfolio.stress_test import portfolio_stress_test
from app.core.atlas.tools.portfolio.factor_exposure import portfolio_factor_exposure
from app.core.atlas.tools.portfolio.classification import portfolio_classification
from app.core.atlas.tools.portfolio.covariance import portfolio_covariance
from app.core.atlas.tools.portfolio.correlation import portfolio_correlation
from app.core.atlas.tools.portfolio.user_portfolio import get_user_simulated_portfolio

# ================================
# --> Imports: portfolio construction
# ================================
from app.core.atlas.tools.portfolio.allocator import portfolio_allocator

# ================================
# --> Imports: watchlist
# ================================
from app.core.atlas.tools.watchlist.get_watchlist import get_watchlist

# ================================
# --> Imports: broker
# ================================
from app.core.atlas.tools.broker.account import account_info
from app.core.atlas.tools.broker.portfolio import get_positions, close_position
from app.core.atlas.tools.broker.trade import propose_trade
from app.core.atlas.tools.broker.options_trade import (
    propose_options_trade,
    propose_multi_leg_options_trade,
)
from app.core.atlas.tools.broker.orders import get_order_impact, get_orders, cancel_order, get_quotes

# ================================
# --> Imports: options
# ================================
from app.core.atlas.tools.options.expirations import get_option_expirations
from app.core.atlas.tools.options.contracts import get_option_contracts
from app.core.atlas.tools.options.chain import get_options_chain
from app.core.atlas.tools.options.quote import get_option_quote
from app.core.atlas.tools.options.price_history import get_option_price_history

# ================================
# --> Imports: research
# ================================
from app.core.atlas.tools.research.macro_research import macro_research
from app.core.atlas.tools.research.earnings_calls import earnings_call_search
from app.core.atlas.tools.research.credit_research import credit_research_search
from app.core.atlas.tools.research.economics_research import economics_research_search
from app.core.atlas.tools.research.user_uploads import user_upload_search
from app.core.atlas.tools.research.tax_research import tax_research_search
from app.core.atlas.tools.research.theory_research import theory_research

# ================================
# --> Imports: market / macro
# ================================
from app.core.atlas.tools.macro.commodity_prices import commodity_prices
from app.core.atlas.tools.macro.us_rates import us_treasury_rates
from app.core.atlas.tools.macro.indicators import macro_indicators

# ================================
# --> Imports: news
# ================================
from app.core.atlas.tools.news import general_news, get_ticker_news, get_press_releases

# ================================
# --> Imports: screener
# ================================
from app.core.atlas.tools.screener.equity_screener import equity_screener
from app.core.atlas.tools.screener.etf_screener import etf_screener


# ==============================================================================
# --> TOOL_REGISTRY: category -> list of @agent_tool-decorated functions
# ==============================================================================

TOOL_REGISTRY: Dict[str, List[Callable]] = {
    "ticker_analytics": [
        ticker_performance, ticker_risk, ticker_factors, ticker_technicals,
    ],
    "ticker_info": [
        get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings,
        get_institutional_holders, get_product_segmentation, get_etf_holdings,
    ],
    "sectors": [
        get_sector_industries, get_group_tickers,
    ],
    "fundamentals": [
        get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm,
        get_price_target_data,
    ],
    "portfolio": [
        portfolio_performance, portfolio_risk, portfolio_stress_test,
        portfolio_factor_exposure, portfolio_classification, portfolio_covariance,
        portfolio_correlation, get_user_simulated_portfolio, get_watchlist,
    ],
    "portfolio_construction": [
        portfolio_allocator,
    ],
    "broker": [
        account_info, get_positions, close_position, propose_trade,
        get_orders, cancel_order, get_quotes, get_order_impact,
    ],
    "options": [
        propose_options_trade, propose_multi_leg_options_trade,
        get_option_expirations, get_option_contracts, get_options_chain,
        get_option_quote, get_option_price_history,
    ],
    "research": [
        macro_research, earnings_call_search, credit_research_search,
        economics_research_search, user_upload_search, tax_research_search,
        theory_research,
    ],
    "market": [
        commodity_prices, us_treasury_rates, macro_indicators,
        general_news, get_ticker_news, get_press_releases,
    ],
    "screener": [
        equity_screener, etf_screener,
    ],
}

# Flat dict: tool_name -> tool dict (name, description, parameters, function)
ALL_TOOLS: Dict[str, Dict[str, Any]] = {
    func.tool["name"]: func.tool
    for funcs in TOOL_REGISTRY.values()
    for func in funcs
}

# Reason: These tools require direct user confirmation and must never be
# delegated to worker agents. They involve real money / trade execution.
CHAT_ONLY_TOOLS: Set[str] = {
    "propose_trade",
    "propose_options_trade",
    "propose_multi_leg_options_trade",
    "close_position",
    "cancel_order",
}

def build_catalogue_description() -> str:
    """Generate a compact category → tool summary with short one-liners.

    Gives the LLM enough context to choose the right tools/categories
    without the full verbose descriptions.
    """
    lines: List[str] = []
    for category in sorted(TOOL_REGISTRY.keys()):
        funcs = TOOL_REGISTRY[category]
        lines.append(f"- **{category}** ({len(funcs)}):")
        for func in funcs:
            desc = func.tool.get("description", "").replace("\n", " ")
            # Reason: Take first sentence only for a compact one-liner
            short = desc.split(".")[0].strip()
            lines.append(f"  - {func.tool['name']}: {short}")

    return "\n".join(lines)
