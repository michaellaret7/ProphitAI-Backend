"""Tool registry for the Dreamer agent.

Curated tools for nightly per-user alpha-generating trade idea generation.
Grouped by purpose: portfolio context, candidate discovery, candidate vetting,
catalyst awareness, and macro regime.
"""

from typing import Callable, List

# ================================
# --> Portfolio context (broker + analytics)
# ================================
from prophitai_tools.broker.portfolio import get_positions
from prophitai_tools.portfolio.performance import portfolio_performance
from prophitai_tools.portfolio.risk import portfolio_risk
from prophitai_tools.portfolio.factor_exposure import portfolio_factor_exposure
from prophitai_tools.portfolio.correlation import portfolio_correlation
from prophitai_tools.portfolio.stress_test import portfolio_stress_test

# ================================
# --> Candidate discovery
# ================================
from prophitai_tools.screener.equity_screener import equity_screener

# ================================
# --> Candidate vetting (ticker analytics)
# ================================
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.factors import ticker_factors
from prophitai_tools.ticker.technicals import ticker_technicals
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.fundamentals.estimates import get_analyst_estimates
from prophitai_tools.ticker.fundamentals.price_target import get_price_target_data

# ================================
# --> Catalysts (news)
# ================================
from prophitai_tools.news.general_news import general_news
from prophitai_tools.news.ticker_news import get_ticker_news

# ================================
# --> Macro regime
# ================================
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators
from prophitai_tools.macro.commodity_prices import commodity_prices


DREAMER_TOOLS: List[Callable] = [
    # portfolio context
    get_positions,
    portfolio_performance,
    portfolio_risk,
    portfolio_factor_exposure,
    portfolio_correlation,
    portfolio_stress_test,
    # discovery
    equity_screener,
    # candidate vetting
    ticker_performance,
    ticker_factors,
    ticker_technicals,
    get_ticker_fundamental_data,
    get_ratios_ttm,
    get_analyst_estimates,
    get_price_target_data,
    # catalysts
    general_news,
    get_ticker_news,
    # macro regime
    us_treasury_rates,
    macro_indicators,
    commodity_prices,
]
