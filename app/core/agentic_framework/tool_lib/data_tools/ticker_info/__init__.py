"""Ticker information and analysis tools.

This module provides tools for ticker-specific data including:
- Stock peer analysis and comparison
- Analyst price targets and consensus
- Product segmentation and revenue breakdowns
- Stock ratings and analyst recommendations
"""

from .peers import (
    get_ticker_peers,
    GET_TICKER_PEERS_TOOL,
)

from .price_target import (
    get_price_target_data,
    GET_PRICE_TARGET_DATA_TOOL,
)

from .product_segmentation import (
    get_product_segmentation,
    GET_PRODUCT_SEGMENTATION_TOOL,
)

from .ratings import (
    get_stock_ratings,
    GET_STOCK_RATINGS_TOOL,
)

__all__ = [
    # Peer analysis
    'get_ticker_peers',
    'GET_TICKER_PEERS_TOOL',

    # Price targets
    'get_price_target_data',
    'GET_PRICE_TARGET_DATA_TOOL',

    # Product segmentation
    'get_product_segmentation',
    'GET_PRODUCT_SEGMENTATION_TOOL',

    # Ratings
    'get_stock_ratings',
    'GET_STOCK_RATINGS_TOOL',
]