"""
Chat Tool Registry - Registers agent-type-specific tools for chat agents.

AgentBase already registers default tools (calculator, think, llm_web_search).
This registry adds ONLY the agent-type-specific tools on top:
- macro_research: Macro research search
- equity_research: Earnings calls, fundamentals, ticker returns, ticker news, estimates, price targets
- portfolio_manager: Alpaca account, orders, and options tools
- user_uploads: User-uploaded document search
- tax_research: Tax documents, IRS forms, instructions, publications
- general: No additional tools (just defaults)
"""

from typing import TYPE_CHECKING

# Macro research tools
from app.core.atlas.tools.base import LLM_WEB_SEARCH_TOOL
from app.core.atlas.tools.foundry.macro_research import MACRO_RESEARCH_SEARCH_TOOL

# Equity research tools
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_fundamentals.statements import (
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
)
from app.core.atlas.tools.ticker.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.core.atlas.tools.data.news.ticker_news import GET_TICKER_NEWS_TOOL
from app.core.atlas.tools.data.fundamentals.ticker_fundamentals.estimates import (
    GET_ANALYST_ESTIMATES_TOOL,
)
from app.core.atlas.tools.data.fundamentals.ticker_info.price_target import (
    GET_PRICE_TARGET_DATA_TOOL,
)

# User upload tools
from app.core.atlas.tools.foundry.user_uploads import USER_UPLOAD_SEARCH_TOOL

# Tax research tools
from app.core.atlas.tools.foundry.tax_research import TAX_RESEARCH_SEARCH_TOOL

# Alpaca tools (portfolio manager)
from app.core.atlas.tools.alpaca import (
    # Account
    ALPACA_ACCT_AND_PORTFOLIO_TOOL,
    PORTFOLIO_HISTORY_TOOL,
    ASSET_LOOKUP_TOOL,
    # Orders
    TRADE_TOOL,
    REPLACE_ORDER_TOOL,
    GET_ORDER_TOOL,
    CANCEL_ORDER_TOOL,
    CANCEL_ALL_ORDERS_TOOL,
    CLOSE_POSITION_TOOL,
    CLOSE_ALL_POSITIONS_TOOL,
    # Options
    OPTIONS_LOOKUP_TOOL,
    OPTIONS_CHAIN_TOOL,
    OPTIONS_TRADE_TOOL,
    EXERCISE_OPTION_TOOL,
    MULTI_LEG_ORDER_TOOL,
    OPTION_BARS_TOOL,
    OPTION_LATEST_QUOTE_TOOL,
    OPTION_SNAPSHOT_TOOL,
)

from app.core.atlas.tools.portfolio.get_user_portfolio import GET_USER_PORTFOLIO_TOOL
from app.core.atlas.tools.portfolio.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL

if TYPE_CHECKING:
    from app.core.atlas.agents.base import AgentBase


def register_tools_for_agent_type(agent: "AgentBase", agent_type: str) -> None:
    """Register agent-type-specific tools.

    Called ONCE when a chat session is created. Default tools (calculator, think,
    llm_web_search) are already registered by AgentBase. This adds only the
    specialized tools.

    Args:
        agent: The agent instance to register tools on.
        agent_type: The type of agent determining which tools to add.
            - "macro_research": Adds macro research search
            - "equity_research": Earnings, fundamentals, returns, news, estimates, price targets
            - "portfolio_manager": Alpaca account, orders, and options
            - "user_uploads": User-uploaded document search
            - "tax_research": Tax documents, IRS forms, instructions
            - "general": No additional tools
    """
    agent.add_tool(**LLM_WEB_SEARCH_TOOL)
    
    if agent_type == "macro_research":
        agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

    elif agent_type == "equity_research":
        agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
        agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
        agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
        agent.add_tool(**GET_TICKER_NEWS_TOOL)
        agent.add_tool(**GET_ANALYST_ESTIMATES_TOOL)
        agent.add_tool(**GET_PRICE_TARGET_DATA_TOOL)
    
    elif agent_type == "portfolio_manager":
        # Account & portfolio
        agent.add_tool(**ALPACA_ACCT_AND_PORTFOLIO_TOOL)
        agent.add_tool(**PORTFOLIO_HISTORY_TOOL)
        agent.add_tool(**ASSET_LOOKUP_TOOL)

        # Orders
        agent.add_tool(**TRADE_TOOL)
        agent.add_tool(**REPLACE_ORDER_TOOL)
        agent.add_tool(**GET_ORDER_TOOL)
        agent.add_tool(**CANCEL_ORDER_TOOL)
        agent.add_tool(**CANCEL_ALL_ORDERS_TOOL)
        agent.add_tool(**CLOSE_POSITION_TOOL)
        agent.add_tool(**CLOSE_ALL_POSITIONS_TOOL)

        # Options
        agent.add_tool(**OPTIONS_LOOKUP_TOOL)
        agent.add_tool(**OPTIONS_CHAIN_TOOL)
        agent.add_tool(**OPTIONS_TRADE_TOOL)
        agent.add_tool(**EXERCISE_OPTION_TOOL)
        agent.add_tool(**MULTI_LEG_ORDER_TOOL)
        agent.add_tool(**OPTION_BARS_TOOL)
        agent.add_tool(**OPTION_LATEST_QUOTE_TOOL)
        agent.add_tool(**OPTION_SNAPSHOT_TOOL)

        # Equity research
        agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
        agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_TOOL)
        agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_TOOL)
        agent.add_tool(**GET_TICKER_NEWS_TOOL)
        agent.add_tool(**GET_ANALYST_ESTIMATES_TOOL)
        agent.add_tool(**GET_PRICE_TARGET_DATA_TOOL)

        agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

        agent.add_tool(**GET_USER_PORTFOLIO_TOOL)
        agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_TOOL)
    
    elif agent_type == "user_uploads":
        agent.add_tool(**USER_UPLOAD_SEARCH_TOOL)

    elif agent_type == "tax_research":
        agent.add_tool(**TAX_RESEARCH_SEARCH_TOOL)
