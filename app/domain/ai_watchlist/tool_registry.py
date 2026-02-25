"""AI Watchlist tool registry - registers analysis tools via tools."""

# --- screener ---
from app.core.atlas.tools.screener.equity_screener import equity_screener
from app.core.atlas.tools.screener.etf_screener import etf_screener

# --- ticker ---
from app.core.atlas.tools.ticker.performance import ticker_performance
from app.core.atlas.tools.ticker.risk import ticker_risk
from app.core.atlas.tools.ticker.factors import ticker_factors
from app.core.atlas.tools.ticker.technicals import ticker_technicals

# --- news ---
from app.core.atlas.tools.news import get_ticker_news, get_press_releases

# --- fundamentals ---
from app.core.atlas.tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from app.core.atlas.tools.ticker.fundamentals.estimates import get_analyst_estimates
from app.core.atlas.tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from app.core.atlas.tools.ticker.fundamentals.price_target import get_price_target_data

# --- info ---
from app.core.atlas.tools.ticker.info.description import get_ticker_info
from app.core.atlas.tools.ticker.info.peers import get_ticker_peers
from app.core.atlas.tools.ticker.info.ratings import get_stock_ratings
from app.core.atlas.tools.ticker.info.institutional_holders import get_institutional_holders
from app.core.atlas.tools.ticker.info.product_segmentation import get_product_segmentation
from app.core.atlas.tools.ticker.info.sectors import get_sector_industries, get_group_tickers

# --- research ---
from app.core.atlas.tools.research.macro_research import macro_research
from app.core.atlas.tools.research.earnings_calls import earnings_call_search


def register_ai_watchlist_tools(agent) -> None:
    """Register screening and analysis tools on the AI watchlist agent.

    Covers: screeners, ticker analysis, fundamentals, info, news, and research.
    """
    for func in [
        # screener
        equity_screener,
        etf_screener,
        # ticker
        ticker_performance,
        ticker_risk,
        ticker_factors,
        ticker_technicals,
        # news
        get_ticker_news,
        get_press_releases,
        # fundamentals
        get_ticker_fundamental_data,
        get_analyst_estimates,
        get_ratios_ttm,
        get_price_target_data,
        # info
        get_ticker_info,
        get_ticker_peers,
        get_stock_ratings,
        get_institutional_holders,
        get_product_segmentation,
        get_sector_industries,
        get_group_tickers,
        # research
        macro_research,
        earnings_call_search,
    ]:
        agent.add_tool(**func.tool)
