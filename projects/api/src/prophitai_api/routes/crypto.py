"""
Cryptocurrency API endpoints.

Provides access to crypto price data and news.
"""

from fastapi import APIRouter, Query, Path
from typing import Optional
from prophitai_api.controllers.crypto import (
    get_crypto_news_general_controller,
    get_crypto_news_by_symbol_controller,
    get_crypto_price_controller,
)

router = APIRouter(tags=["Cryptocurrency 🪙"])


@router.get("/crypto/news")
async def get_crypto_news_general(
    limit: int = Query(1000, gt=0, le=1000, description="Maximum number of news items to return"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)"),
):
    """
    Get general cryptocurrency news from FMP

    Args:
        limit: Maximum number of news items to return (default: 1000, max: 1000)
        from_date: Optional start date for filtering news (YYYY-MM-DD format)
        to_date: Optional end date for filtering news (YYYY-MM-DD format)

    Returns:
        Cryptocurrency news items with published date, title, publisher, site, text content, image URL, and article URL

    Example: GET /api/crypto/news?limit=100
    """
    return await get_crypto_news_general_controller(
        limit=limit,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/crypto/{symbol}/news")
async def get_crypto_news_by_symbol(
    symbol: str = Path(..., description="Crypto symbol (e.g., 'BTC', 'ETH', 'BTCUSD')"),
    limit: int = Query(250, gt=0, le=250, description="Maximum number of news items to return"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)"),
):
    """
    Get cryptocurrency news for a specific symbol from FMP

    Args:
        symbol: Crypto symbol (e.g., 'BTC', 'ETH', 'BTCUSD')
        limit: Maximum number of news items to return (default: 250, max: 250)
        from_date: Optional start date for filtering news (YYYY-MM-DD format)
        to_date: Optional end date for filtering news (YYYY-MM-DD format)

    Returns:
        Cryptocurrency news items with published date, title, publisher, site, text content, image URL, and article URL

    Example: GET /api/crypto/BTCUSD/news?limit=50
    """
    return await get_crypto_news_by_symbol_controller(
        symbol=symbol,
        limit=limit,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/crypto/{symbol}/price")
async def get_crypto_price(
    symbol: str = Path(..., description="Crypto symbol (e.g., 'BTCUSD', 'ETHUSD')"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD format)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD format)"),
    technical_indicators: bool = Query(True, description="Include technical indicators (SMA, RSI, MACD, Bollinger Bands, ADX, Ichimoku, TD Sequential)"),
):
    """
    Get cryptocurrency EOD (end-of-day) price data for a specific symbol from FMP

    Args:
        symbol: Crypto symbol (e.g., 'BTCUSD', 'ETHUSD')
        from_date: Optional start date for filtering price data (YYYY-MM-DD format)
        to_date: Optional end date for filtering price data (YYYY-MM-DD format)
        technical_indicators: Include technical indicators in response (default: True)

    Returns:
        OHLCV price data with optional technical indicators:
        - OHLCV: Open, High, Low, Close, Volume
        - Moving Averages: SMA8, SMA20, SMA50, SMA100, SMA200
        - Momentum: RSI (14-period)
        - Trend: MACD (12, 26, 9), ADX (14-period)
        - Volatility: Bollinger Bands (20-period, 2 std dev)
        - Cloud: Ichimoku Cloud (9, 26, 52)
        - Timing: TD Sequential (buy/sell setups and countdowns)

    Example: GET /api/crypto/BTCUSD/price?from_date=2024-01-01&to_date=2024-12-31
    """
    return await get_crypto_price_controller(
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        technical_indicators=technical_indicators,
    )
