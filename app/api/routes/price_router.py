from fastapi import APIRouter, Query, Depends
from typing import List, Literal
from app.api.controller.price import (
    get_stock_prices_controller,
    get_quote_controller,
    get_stock_prices_intraday_controller,
    index_price_data_controller,
    get_price_change_controller,
)
from app.models.price_models import StockPriceRequest

router = APIRouter(tags=["Stock Prices 💵"])

def parse_stock_price_request(
    tickers: List[str] = Query(..., description="List of stock ticker symbols", min_length=1),
    days: int = Query(..., gt=0, description="Number of days of historical data to retrieve")
) -> StockPriceRequest:
    """Parse and validate query parameters into StockPriceRequest model"""
    return StockPriceRequest(tickers=tickers, days=days)

@router.get("/price/stocks")
async def get_stock_prices(
    request: StockPriceRequest = Depends(parse_stock_price_request)
):
    """
    Get OHLCV stock price data for one or more tickers over the last X days

    Args:
        request: Validated request containing tickers and days parameters
            - tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
            - days: Number of days of historical price data to retrieve

    Returns:
        OHLCV data including open, high, low, close, and volume for each date
    """
    return await get_stock_prices_controller(tickers=request.tickers, days=request.days)


@router.get("/price/quote")
async def get_quote(
    ticker: str = Query(
        ...,
        description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')",
        min_length=1,
        max_length=10,
    ),
):
    """
    Get current quote data for a single ticker.

    Returns real-time market data including:
    - Current price, open, previous close
    - Day high/low, 52-week high/low
    - Volume, average volume
    - Market cap, shares outstanding
    - PE ratio, EPS
    - Price change and percent change

    Example: GET /api/price/quote?ticker=AAPL
    """
    return await get_quote_controller(ticker=ticker)


@router.get("/price/stocks/intraday")
async def get_stock_prices_intraday(
    tickers: List[str] = Query(..., description="List of stock ticker symbols", min_length=1),
    days: int = Query(..., gt=0, description="Number of days of historical data to retrieve"),
    frequency: Literal['15mins', 'hourly'] = Query('15mins', description="Data interval - '15mins' or 'hourly'")
):
    """
    Get intraday OHLCV stock price data for one or more tickers.

    Returns 15-minute or hourly interval price data from the Prices table.

    Args:
        tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT'])
        days: Number of days of historical data to retrieve
        frequency: Data interval - '15mins' (default) or 'hourly'

    Returns:
        OHLCV data with datetime, open, high, low, close, and volume for each interval

    Example: GET /api/price/stocks/intraday?tickers=AAPL&tickers=MSFT&days=5&frequency=15mins
    """
    return await get_stock_prices_intraday_controller(
        tickers=[t.upper() for t in tickers],
        days=days,
        frequency=frequency
    )


@router.get("/price/index")
async def index_price_data(
    ticker: str = Query(..., description="Stock ticker symbol (e.g., '^GSPC'). You must add the ^ symbol to the beginning of the index symbol."),
    days: int = Query(..., gt=0, description="Number of days back to index")
):
    """
    Index price data for a single ticker.

    Args:
        ticker: Stock ticker symbol
        days: Number of days back to index data from

    Returns:
        Indexed price data payload
    """
    return await index_price_data_controller(ticker=ticker, days=days)


@router.get("/price/price-change")
async def get_price_change(
    tickers: List[str] = Query(
        ...,
        description="List of stock ticker symbols (e.g., ['AAPL', 'MSFT'])",
        min_length=1,
    ),
):
    """
    Get price change percentages for multiple tickers across various time periods.

    Returns percentage changes (as decimals) for:
    - 1D, 5D: Short-term daily changes
    - 1M, 3M, 6M: Monthly changes
    - ytd: Year-to-date change
    - 1Y, 3Y, 5Y, 10Y: Annual changes
    - max: All-time change

    Values are decimals (e.g., 0.05 = 5% gain, -0.03 = 3% loss)

    Example: GET /api/price/price-change?tickers=AAPL&tickers=MSFT
    """
    return await get_price_change_controller(tickers=[t.upper() for t in tickers])
