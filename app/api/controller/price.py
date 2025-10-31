from fastapi import HTTPException
from typing import Dict, Any, List
from app.services.shared import PriceService, TickerReturnsService
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors


@handle_controller_errors
async def get_stock_prices_controller(tickers: List[str], days: int) -> Dict[str, Any]:
    """
    Controller to handle stock price data retrieval for multiple tickers
    """
    # Delegate to service
    service = PriceService()
    data = service.get_stock_prices(tickers=tickers, days=days)

    return ok_envelope(
        message="Stock price data retrieved successfully",
        kind="price#stockPrices",
        resource_id=",".join(tickers),
        self_link=f"/api/price/stocks",
        counts=data['counts'],
        payload=data['payload'],
    )


@handle_controller_errors
async def get_ticker_returns_controller(
    *,
    ticker: str,
    years: int = 1,
) -> Dict[str, Any]:
    """
    Controller to handle ticker daily returns retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: ticker:returns:{ticker}:{years}
    """
    if not ticker:
        raise ValueError("ticker is required")

    # Generate cache key
    cache_key = f"ticker:returns:{ticker.upper()}:{years}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute returns
    service = TickerReturnsService()
    returns_data = service.get_ticker_returns(ticker=ticker, years=years)

    # Build response
    response = ok_envelope(
        message=f"Daily returns for {ticker.upper()} retrieved successfully",
        kind="ticker#returns",
        resource_id=ticker.upper(),
        self_link=f"/api/tickers/{ticker.upper()}/returns?years={years}",
        payload=returns_data,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response
