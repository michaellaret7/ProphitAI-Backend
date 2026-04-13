"""Central tool registry for ProphitAI domain tools.

Imports all @agent_tool-decorated functions and exposes them as a flat list
for injection into the Agent constructor via ``Agent(deferred_tools=ALL_TOOL_FUNCTIONS)``.

Each tool is decorated with ``@agent_tool(category="category_name")`` so
build_deferred_tools_data can group them automatically.
"""

from typing import Callable

# ================================
# --> Imports: ticker analytics
# ================================
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.technicals import ticker_technicals

# ================================
# --> Imports: ticker info
# ================================
from prophitai_tools.ticker.info.description import get_ticker_info, get_etf_info
from prophitai_tools.ticker.info.peers import get_ticker_peers
from prophitai_tools.ticker.info.ratings import get_stock_ratings
from prophitai_tools.ticker.info.institutional_holders import get_institutional_holders
from prophitai_tools.ticker.info.product_segmentation import get_product_segmentation
from prophitai_tools.ticker.info.etf_holdings import get_etf_holdings

# ================================
# --> Imports: sectors
# ================================
from prophitai_tools.ticker.info.sectors import get_sector_industries, get_group_tickers

# ================================
# --> Imports: fundamentals
# ================================
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.estimates import get_analyst_estimates
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.fundamentals.price_target import get_price_target_data

# ================================
# --> Imports: portfolio
# ================================
from prophitai_tools.portfolio.performance import portfolio_performance
from prophitai_tools.portfolio.risk import portfolio_risk
from prophitai_tools.portfolio.stress_test import portfolio_stress_test
from prophitai_tools.portfolio.factor_exposure import portfolio_factor_exposure
from prophitai_tools.portfolio.classification import portfolio_classification
from prophitai_tools.portfolio.covariance import portfolio_covariance
from prophitai_tools.portfolio.correlation import portfolio_correlation
from prophitai_tools.portfolio.user_portfolio import get_user_simulated_portfolio

# ================================
# --> Imports: portfolio construction
# ================================
from prophitai_tools.portfolio.allocator import portfolio_allocator

# ================================
# --> Imports: watchlist
# ================================
from prophitai_tools.watchlist.get_watchlist import get_watchlist

# ================================
# --> Imports: broker
# ================================
from prophitai_tools.broker.account import account_info
from prophitai_tools.broker.portfolio import get_positions, close_position
from prophitai_tools.broker.trade import propose_trade
from prophitai_tools.broker.options_trade import (
    propose_options_trade,
    propose_multi_leg_options_trade,
)
from prophitai_tools.broker.orders import get_order_impact, get_orders, cancel_order, get_quotes

# ================================
# --> Imports: options
# ================================
from prophitai_tools.options.expirations import get_option_expirations
from prophitai_tools.options.contracts import get_option_contracts
from prophitai_tools.options.chain import get_options_chain
from prophitai_tools.options.quote import get_option_quote
from prophitai_tools.options.price_history import get_option_price_history

# ================================
# --> Imports: research
# ================================
from prophitai_tools.research.macro_research import macro_research_search
from prophitai_tools.research.earnings_calls import earnings_call_search
from prophitai_tools.research.credit_research import credit_research_search
from prophitai_tools.research.economics_research import economics_research_search
from prophitai_tools.research.user_uploads import user_upload_search
from prophitai_tools.research.tax_research import tax_research_search
from prophitai_tools.research.theory_research import theory_research
from prophitai_tools.research.strategy_research import strategy_research

# ================================
# --> Imports: market / macro
# ================================
from prophitai_tools.macro.commodity_prices import commodity_prices
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators

# ================================
# --> Imports: news
# ================================
from prophitai_tools.news.general_news import general_news
from prophitai_tools.news.ticker_news import get_ticker_news
from prophitai_tools.news.press_releases import get_press_releases

# ================================
# --> Imports: screener
# ================================
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.screener.etf_screener import etf_screener

# ================================
# --> Imports: institutional
# ================================
from prophitai_tools.institutional.fund_holdings import get_fund_13f_holdings

# ================================
# --> Imports: render (infra)
# ================================
from prophitai_tools.render.deploys import (
    list_deploys, get_deploy, trigger_deploy, cancel_deploy, rollback_deploy,
)
from prophitai_tools.render.services import (
    create_render_service, list_render_services, get_render_service,
    list_instances, restart_service, suspend_service, resume_service,
)
from prophitai_tools.render.env_vars import list_env_vars, set_env_var, delete_env_var
from prophitai_tools.render.logs import get_render_logs, get_render_log_labels

# ================================
# --> Imports: sandbox
# ================================
from prophitai_tools.sandbox.lifecycle import start_sandbox, close_sandbox, get_sandbox_status
from prophitai_tools.sandbox.execution import sandbox_bash
from prophitai_tools.sandbox.scaffolding import scaffold_strategy
from prophitai_tools.sandbox.github import create_pull_request
from prophitai_tools.sandbox.dev_tools.edit import sandbox_edit
from prophitai_tools.sandbox.dev_tools.read import sandbox_read
from prophitai_tools.sandbox.dev_tools.write import sandbox_write
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob
from prophitai_tools.sandbox.dev_tools.grep import sandbox_grep


# ==============================================================================
# --> ALL_TOOL_FUNCTIONS: flat list of every @agent_tool-decorated function
# ==============================================================================

ALL_TOOL_FUNCTIONS: list[Callable] = [
    # ticker_analytics
    ticker_performance, ticker_risk, ticker_factors, ticker_technicals,
    # ticker_info
    get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings,
    get_institutional_holders, get_product_segmentation, get_etf_holdings,
    # sectors
    get_sector_industries, get_group_tickers,
    # fundamentals
    get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm,
    get_price_target_data,
    # portfolio
    portfolio_performance, portfolio_risk, portfolio_stress_test,
    portfolio_factor_exposure, portfolio_classification, portfolio_covariance,
    portfolio_correlation, get_user_simulated_portfolio, get_watchlist,
    # portfolio_construction
    portfolio_allocator,
    # broker
    account_info, get_positions, close_position, propose_trade,
    get_orders, cancel_order, get_quotes, get_order_impact,
    # options
    propose_options_trade, propose_multi_leg_options_trade,
    get_option_expirations, get_option_contracts, get_options_chain,
    get_option_quote, get_option_price_history,
    # research
    macro_research_search, earnings_call_search, credit_research_search,
    economics_research_search, user_upload_search, tax_research_search,
    theory_research, strategy_research,
    # market
    commodity_prices, us_treasury_rates, macro_indicators,
    general_news, get_ticker_news, get_press_releases,
    # screener
    equity_screener, etf_screener,
    # institutional
    get_fund_13f_holdings,
    # render (infra)
    list_deploys, get_deploy, trigger_deploy, cancel_deploy, rollback_deploy,
    create_render_service, list_render_services, get_render_service,
    list_instances, restart_service, suspend_service, resume_service,
    list_env_vars, set_env_var, delete_env_var,
    get_render_logs, get_render_log_labels,
    # sandbox
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_bash, scaffold_strategy, create_pull_request,
    sandbox_read, sandbox_write, sandbox_edit, sandbox_glob, sandbox_grep,
]

# Reason: Render deployment and sandbox tools are infrastructure / dev-only
# and should not be available to the chat agent.
_EXCLUDED_FROM_CHAT: set[Callable] = {
    # render
    list_deploys, get_deploy, trigger_deploy, cancel_deploy, rollback_deploy,
    create_render_service, list_render_services, get_render_service,
    list_instances, restart_service, suspend_service, resume_service,
    list_env_vars, set_env_var, delete_env_var,
    get_render_logs, get_render_log_labels,
    # sandbox
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_bash, scaffold_strategy, sandbox_read, sandbox_write, sandbox_edit, sandbox_glob, sandbox_grep,
    create_pull_request,
}

CHAT_TOOL_FUNCTIONS: list[Callable] = [
    fn for fn in ALL_TOOL_FUNCTIONS if fn not in _EXCLUDED_FROM_CHAT
]

# Reason: These tools require direct user confirmation and must never be
# delegated to worker agents. They involve real money / trade execution.
CHAT_ONLY_TOOLS: set[str] = {
    "propose_trade",
    "propose_options_trade",
    "propose_multi_leg_options_trade",
    "close_position",
    "cancel_order",
}
