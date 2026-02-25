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

# --- alpaca ---
from app.core.atlas.tools.alpaca.account import account_info, account_activities
from app.core.atlas.tools.alpaca.portfolio import (
    get_position, get_positions, close_position, get_portfolio_history,
)
from app.core.atlas.tools.alpaca.trade import (
    submit_trade, get_orders, cancel_order, cancel_all_orders, get_asset,
)

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
        # alpaca - account
        account_info,
        account_activities,
        # alpaca - portfolio
        get_position,
        get_positions,
        close_position,
        get_portfolio_history,
        # alpaca - trade
        submit_trade,
        get_orders,
        cancel_order,
        cancel_all_orders,
        get_asset,
    ]:
        agent.add_tool(**func.tool)
