"""Tool registry for the Trade Idea agent.

Core tools are loaded into the agent's context immediately.
Deferred tools are available on-demand via the register_tools mechanism.
"""

from typing import Callable

# ================================
# --> Research tools
# ================================
from prophitai_tools.research.theory_research import theory_research
from prophitai_tools.research.macro_research import macro_research_search
from prophitai_tools.research.economics_research import economics_research_search
from prophitai_tools.research.credit_research import credit_research_search
from prophitai_tools.research.earnings_calls import earnings_call_search

# ================================
# --> News tools
# ================================
from prophitai_tools.news.general_news import general_news
from prophitai_tools.news.ticker_news import get_ticker_news

# ================================
# --> Ticker analytics
# ================================
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.risk import ticker_risk
from prophitai_tools.ticker.technicals import ticker_technicals

# ================================
# --> Fundamentals
# ================================
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.estimates import get_analyst_estimates
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.fundamentals.price_target import get_price_target_data

# ================================
# --> Ticker info
# ================================
from prophitai_tools.ticker.info.description import get_ticker_info, get_etf_info

# ================================
# --> Macro tools
# ================================
from prophitai_tools.macro.commodity_prices import commodity_prices
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators

# ================================
# --> Screener tools
# ================================
from prophitai_tools.screener.equity_screener import equity_screener
from prophitai_tools.screener.etf_screener import etf_screener


TRADE_IDEA_TOOLS: list[Callable] = [
    # research (core — longer-term portfolio ideas)
    theory_research,
    macro_research_search,
    economics_research_search,
    credit_research_search,
    earnings_call_search,

    # news (current context)
    general_news,
    get_ticker_news,

    # ticker data (thesis support)
    ticker_performance,
    ticker_factors,
    ticker_risk,

    # fundamentals (core for longer-term ideas)
    get_ticker_fundamental_data,
    get_analyst_estimates,

    # macro data
    commodity_prices,
    us_treasury_rates,
    macro_indicators,

    # deeper ticker analytics
    ticker_technicals,
    get_ratios_ttm,
    get_price_target_data,

    # ticker info
    get_ticker_info,
    get_etf_info,

    # screeners
    equity_screener,
    etf_screener,
]
