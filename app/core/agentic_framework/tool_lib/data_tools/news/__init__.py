"""News and media data tools.

This module provides tools for accessing various types of financial news:
- General market news and headlines
- Company-specific news and press releases
- Merger & acquisition announcements
- Price target news from analysts
"""

from .general_news import (
    get_general_news,
    GET_GENERAL_NEWS_TOOL,
)

from .ticker_news import (
    get_ticker_news,
    GET_TICKER_NEWS_TOOL,
)

from .press_releases import (
    get_press_releases,
    GET_PRESS_RELEASES_TOOL,
)

from .m_and_a_news import (
    get_mergers_acquisitions,
    GET_MERGERS_ACQUISITIONS_TOOL,
)

from .price_target_news import (
    get_price_target_news,
    GET_PRICE_TARGET_NEWS_TOOL,
)

__all__ = [
    # General news
    'get_general_news',
    'GET_GENERAL_NEWS_TOOL',

    # Ticker news
    'get_ticker_news',
    'GET_TICKER_NEWS_TOOL',

    # Press releases
    'get_press_releases',
    'GET_PRESS_RELEASES_TOOL',

    # M&A news
    'get_mergers_acquisitions',
    'GET_MERGERS_ACQUISITIONS_TOOL',

    # Price target news
    'get_price_target_news',
    'GET_PRICE_TARGET_NEWS_TOOL',
]