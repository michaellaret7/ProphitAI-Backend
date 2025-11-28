import asyncio
from fastapi import HTTPException
from typing import Dict, Any, List
from app.services.shared import PriceService
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.pull_fmp_data import FMP_API_DATA
from typing import Literal

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
async def get_quote_controller(ticker: str) -> Dict[str, Any]:
    """
    Controller to retrieve current quote data for a single ticker.

    Returns real-time quote information including price, volume, market cap,
    day high/low, 52-week high/low, and other market data.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Response envelope with quote payload
    """
    fmp = FMP_API_DATA()
    data = await asyncio.to_thread(fmp.get_full_quote, ticker.upper())

    if not data:
        raise HTTPException(status_code=404, detail=f"Quote not found for ticker {ticker.upper()}")

    return ok_envelope(
        message=f"Quote for {ticker.upper()} retrieved successfully",
        kind="price#quote",
        resource_id=ticker.upper(),
        self_link=f"/api/price/quote?ticker={ticker.upper()}",
        payload=data[0] if isinstance(data, list) and len(data) > 0 else data,
    )

@handle_controller_errors
async def get_stock_prices_intraday_controller(tickers: List[str], days: int, frequency: Literal['15mins', 'hourly'] = '15mins') -> Dict[str, Any]:
    """
    Controller to handle intraday stock price data retrieval for multiple tickers.

    Args:
        tickers: List of stock ticker symbols
        days: Number of days of historical data
        frequency: Data interval - '15mins' or 'hourly'

    Returns:
        Response envelope with intraday OHLCV data
    """
    service = PriceService()
    data = service.get_stock_prices_intraday(tickers=tickers, days=days, frequency=frequency)

    return ok_envelope(
        message="Stock intraday price data retrieved successfully",
        kind="price#stockPricesIntraday",
        resource_id=",".join(tickers),
        self_link=f"/api/price/stocks/intraday?tickers={','.join(tickers)}&days={days}&frequency={frequency}",
        counts=data['counts'],
        payload=data['payload'],
    )

if __name__ == "__main__":
    print(asyncio.run(get_stock_prices_intraday_controller(tickers=['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'IBM', 'ORCL', 'SAP'], days=200, frequency='15mins')))