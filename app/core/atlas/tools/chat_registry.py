"""Chat Tool Registry - Registers all available tools for chat agents.

AgentBase already registers default tools (calculator, think).
This registry adds all specialized tools on top.
"""

from typing import TYPE_CHECKING

# --- base ---
from app.core.atlas.tools.base import llm_web_search

# --- research ---
from app.core.atlas.tools.research.macro_research import macro_research
from app.core.atlas.tools.research.earnings_calls import earnings_call_search
from app.core.atlas.tools.research.user_uploads import user_upload_search
from app.core.atlas.tools.research.tax_research import tax_research_search
from app.core.atlas.tools.research.theory_research import theory_research

# --- ticker ---
from app.core.atlas.tools.ticker.performance import ticker_performance
from app.core.atlas.tools.ticker.risk import ticker_risk

# --- news ---
from app.core.atlas.tools.news import get_ticker_news

# --- fundamentals ---
from app.core.atlas.tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools.ticker.fundamentals.price_target import get_price_target_data

# --- portfolio ---
from app.core.atlas.tools.portfolio.performance import portfolio_performance
from app.core.atlas.tools.portfolio.user_portfolio import get_user_simulated_portfolio

# --- watchlist ---
from app.core.atlas.tools.watchlist.get_watchlist import get_watchlist

# --- broker ---
from app.core.atlas.tools.broker.account import account_info
from app.core.atlas.tools.broker.portfolio import (
    get_positions, close_position,
)
from app.core.atlas.tools.broker.trade import propose_trade
from app.core.atlas.tools.broker.options_trade import (
    propose_options_trade, propose_multi_leg_options_trade,
)
from app.core.atlas.tools.broker.orders import (
    get_order_impact, get_orders, cancel_order, get_quotes,
)
from app.core.atlas.tools.screener.equity_screener import equity_screener
from app.core.atlas.tools.screener.etf_screener import etf_screener

# --- options ---
from app.core.atlas.tools.options.expirations import get_option_expirations
from app.core.atlas.tools.options.contracts import get_option_contracts
from app.core.atlas.tools.options.chain import get_options_chain
from app.core.atlas.tools.options.quote import get_option_quote
from app.core.atlas.tools.options.price_history import get_option_price_history

if TYPE_CHECKING:
    from app.core.atlas.agents.base import AgentBase


def register_chat_tools(agent: "AgentBase") -> None:
    """Register all specialized tools on the chat agent."""
    for func in [
        # base
        llm_web_search,
        # research
        macro_research,
        earnings_call_search,
        user_upload_search,
        tax_research_search,
        theory_research,
        # ticker
        ticker_performance,
        ticker_risk,
        # news
        get_ticker_news,
        # fundamentals
        get_ticker_fundamental_data,
        get_analyst_estimates,
        get_price_target_data,
        # portfolio
        portfolio_performance,
        get_user_simulated_portfolio,
        # watchlist
        get_watchlist,
        # broker - account
        account_info,
        # broker - portfolio
        get_positions,
        close_position,
        # broker - trade & orders
        propose_trade,
        # broker - options trade
        propose_options_trade,
        propose_multi_leg_options_trade,
        get_orders,
        cancel_order,
        get_quotes,
        get_order_impact,
        # screener
        equity_screener,
        etf_screener,
        # options
        get_option_expirations,
        get_option_contracts,
        get_options_chain,
        get_option_quote,
        get_option_price_history,
    ]:
        agent.add_tool(**func.tool)
