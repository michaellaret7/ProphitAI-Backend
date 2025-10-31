"""
Ticker-specific data controller.

Handles fetching fundamental financial data (income statements, balance sheets,
cash flow statements, and financial ratios) for individual tickers.
"""

from typing import Any, Dict

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.repositories.fundamental_data import get_all_fundamentals
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_ticker_fundamentals_controller(
    *,
    ticker: str,
    quarters_back: int = 4,
) -> Dict[str, Any]:
    """
    Retrieve all fundamental financial data for a ticker.

    Returns income statements, balance sheets, cash flow statements,
    and financial ratios in a single response.

    Cache TTL: 1 day (86400s)

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        quarters_back: Number of historical quarters to return (default: 4)

    Returns:
        Response envelope with fundamental data payload
    """
    # Generate cache key
    cache_key = f"ticker:fundamentals:{ticker.upper()}:{quarters_back}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch from database
    fundamentals = get_all_fundamentals(
        ticker=ticker,
        quarters_back=quarters_back,
    )

    # Build response envelope
    response = ok_envelope(
        message=f"Fundamental data for {ticker.upper()} retrieved successfully",
        kind="ticker#fundamentals",
        resource_id=ticker.upper(),
        self_link=f"/api/ticker/fundamentals?ticker={ticker.upper()}&quartersBack={quarters_back}",
        payload=fundamentals,
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response
