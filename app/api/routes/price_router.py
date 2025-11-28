from fastapi import APIRouter, Query, Depends
from typing import List, Literal
from app.api.controller.price import get_stock_prices_controller, get_quote_controller, get_stock_prices_intraday_controller
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
