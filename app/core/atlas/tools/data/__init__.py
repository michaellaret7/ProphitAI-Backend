"""Data tools for Atlas agents.

This module provides data retrieval tools including:
- Screening tools (equity and ETF screeners)
- Fundamental data tools (financial statements, estimates, ratios)
- Ticker information tools (info, peers, price targets, ratings)
- Corporate actions tools (earnings transcripts)
- ETF tools (info, holdings)
- Factor benchmark tools (industry, sub-industry)
- Sector tools (hierarchy, PE ratios, performance)
- News tools (general, ticker, press releases, M&A, price targets)
"""

from .screening import (
    equity_screener,
    EQUITY_SCREENER_TOOL,
    etf_screener,
    ETF_SCREENER_TOOL,
)

from .fundamentals import (
    # Ticker fundamentals
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    GET_ANALYST_ESTIMATES_TOOL,
    GET_RATIOS_TTM_TOOL,
    get_fundamental_data,
    get_analyst_estimates,
    get_ratios_ttm,
    # Ticker info
    GET_TICKER_INFO_TOOL,
    GET_TICKER_PEERS_TOOL,
    GET_PRICE_TARGET_DATA_TOOL,
    GET_PRODUCT_SEGMENTATION_TOOL,
    GET_STOCK_RATINGS_TOOL,
    get_ticker_info,
    get_ticker_peers,
    get_price_target_data,
    get_product_segmentation,
    get_stock_ratings,
    get_institutional_holders,
)

from .corporate_actions import (
    GET_EARNINGS_TRANSCRIPTS_TOOL,
    get_earnings_call_transcripts,
)

from .etf import (
    GET_ETF_INFO_TOOL,
    GET_ETF_HOLDINGS_TOOL,
    get_etf_info,
    get_etf_holdings,
)

from .factors import (
    GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
    GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
    get_industry_factor_benchmark,
    get_sub_industry_factor_benchmark,
)

from .sectors import (
    GET_GROUP_TICKERS_TOOL,
    GET_SECTOR_INDUSTRIES_TOOL,
    GET_SECTOR_PE_TOOL,
    GET_SECTOR_PERFORMANCE_TOOL,
    get_group_tickers,
    get_sector_industries,
    get_sector_pe,
    get_sector_performance,
    SECTOR_MAPPING,
    FMP_TO_EQUITY_SECTOR,
)

from .news import (
    GET_GENERAL_NEWS_TOOL,
    GET_TICKER_NEWS_TOOL,
    GET_PRESS_RELEASES_TOOL,
    GET_MERGERS_ACQUISITIONS_TOOL,
    GET_PRICE_TARGET_NEWS_TOOL,
    get_general_news,
    get_ticker_news,
    get_press_releases,
    get_mergers_acquisitions,
    get_price_target_news,
)

__all__ = [
    # Screening tools
    'equity_screener',
    'EQUITY_SCREENER_TOOL',
    'etf_screener',
    'ETF_SCREENER_TOOL',
    # Ticker fundamentals tools
    'GET_TICKER_FUNDAMENTAL_DATA_TOOL',
    'GET_ANALYST_ESTIMATES_TOOL',
    'GET_RATIOS_TTM_TOOL',
    'get_fundamental_data',
    'get_analyst_estimates',
    'get_ratios_ttm',
    # Ticker info tools
    'GET_TICKER_INFO_TOOL',
    'GET_TICKER_PEERS_TOOL',
    'GET_PRICE_TARGET_DATA_TOOL',
    'GET_PRODUCT_SEGMENTATION_TOOL',
    'GET_STOCK_RATINGS_TOOL',
    'get_ticker_info',
    'get_ticker_peers',
    'get_price_target_data',
    'get_product_segmentation',
    'get_stock_ratings',
    'get_institutional_holders',
    # Corporate actions tools
    'GET_EARNINGS_TRANSCRIPTS_TOOL',
    'get_earnings_call_transcripts',
    # ETF tools
    'GET_ETF_INFO_TOOL',
    'GET_ETF_HOLDINGS_TOOL',
    'get_etf_info',
    'get_etf_holdings',
    # Factor benchmark tools
    'GET_INDUSTRY_FACTOR_BENCHMARK_TOOL',
    'GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL',
    'get_industry_factor_benchmark',
    'get_sub_industry_factor_benchmark',
    # Sector tools
    'GET_GROUP_TICKERS_TOOL',
    'GET_SECTOR_INDUSTRIES_TOOL',
    'GET_SECTOR_PE_TOOL',
    'GET_SECTOR_PERFORMANCE_TOOL',
    'get_group_tickers',
    'get_sector_industries',
    'get_sector_pe',
    'get_sector_performance',
    'SECTOR_MAPPING',
    'FMP_TO_EQUITY_SECTOR',
    # News tools
    'GET_GENERAL_NEWS_TOOL',
    'GET_TICKER_NEWS_TOOL',
    'GET_PRESS_RELEASES_TOOL',
    'GET_MERGERS_ACQUISITIONS_TOOL',
    'GET_PRICE_TARGET_NEWS_TOOL',
    'get_general_news',
    'get_ticker_news',
    'get_press_releases',
    'get_mergers_acquisitions',
    'get_price_target_news',
]
