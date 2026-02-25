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


@handle_controller_errors
async def index_price_data_controller(ticker: str, days: int) -> Dict[str, Any]:
    """
    Controller to handle indexing of price data for a single ticker.
    """
    from datetime import timedelta
    from app.utils.time_utils import get_current_utc_time
    to_date = get_current_utc_time()
    from_date = to_date - timedelta(days=days)

    fmp = FMP_API_DATA()
    data = await asyncio.to_thread(fmp.get_daily_prices_for_ticker, ticker, from_date, to_date)

    return ok_envelope(
        message="Price data indexed successfully",
        kind="price#priceDataIndexed",
        resource_id=ticker,
        self_link=f"/api/price/index?ticker={ticker}&days={days}",
        payload=data,
    )

@handle_controller_errors
async def get_price_change_controller(tickers: List[str]) -> Dict[str, Any]:
    """
    Controller to handle price change data retrieval for multiple tickers.

    Returns price change percentages (as decimals) for various time periods:
    1D, 5D, 1M, 3M, 6M, ytd, 1Y, 3Y, 5Y, 10Y, max

    Args:
        tickers: List of stock ticker symbols

    Returns:
        Response envelope with price change data for each ticker
    """
    fmp = FMP_API_DATA()

    tasks = [asyncio.to_thread(fmp.get_stock_price_change, ticker=ticker) for ticker in tickers]
    results = await asyncio.gather(*tasks)

    # Flatten results (each API call returns a list with one item)
    payload = [item for result in results if result for item in result]

    return ok_envelope(
        message="Price change data retrieved successfully",
        kind="price#priceChange",
        resource_id=",".join(tickers),
        self_link=f"/api/price/price-change?tickers={','.join(tickers)}",
        counts={"totalItems": len(payload), "currentItemCount": len(payload)},
        payload=payload,
    )


@handle_controller_errors
async def get_batch_quotes_controller(tickers: List[str]) -> Dict[str, Any]:
    """
    Controller to retrieve batch quote data for multiple tickers.

    Uses FMP's native batch quote API which accepts comma-separated symbols.
    No caching since this is real-time price data.

    Args:
        tickers: List of stock ticker symbols (max 20)

    Returns:
        Response envelope with batch quotes payload
    """
    fmp = FMP_API_DATA()

    # Reason: Use FMP's native batch endpoint for efficiency
    data = await asyncio.to_thread(fmp.get_batch_quote, tickers)

    if not data:
        data = []

    # Build a map of ticker -> quote data for easy lookup
    quotes_map: Dict[str, Dict[str, Any]] = {}
    found_tickers: List[str] = []

    for quote in data:
        symbol = quote.get("symbol")
        if symbol:
            quotes_map[symbol] = quote
            found_tickers.append(symbol)

    # Identify missing tickers
    missing_tickers = [t for t in tickers if t not in quotes_map]

    return ok_envelope(
        message=f"Batch quotes retrieved successfully ({len(found_tickers)} found, {len(missing_tickers)} not found)",
        kind="price#batchQuotes",
        resource_id=",".join(sorted(tickers)),
        self_link="/api/price/quotes/batch",
        counts={
            "totalRequested": len(tickers),
            "found": len(found_tickers),
            "notFound": len(missing_tickers)
        },
        payload={
            "data": quotes_map,
            "missing_tickers": missing_tickers
        },
    )
