from fastapi import APIRouter, Query, Depends
from typing import List
from app.api.controller.price import get_stock_prices_controller, get_ticker_returns_controller
from app.models.price_models import StockPriceRequest

router = APIRouter()

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
    Get stock price data for one or more tickers over the last X days

    Args:
        request: Validated request containing tickers and days parameters
            - tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
            - days: Number of days of historical price data to retrieve
    """
    return await get_stock_prices_controller(tickers=request.tickers, days=request.days)


@router.get("/tickers/{ticker}/returns")
async def get_ticker_returns(
    ticker: str,
    years: int = Query(1, description="Number of years of historical data (1-10)", ge=1, le=10),
):
    """
    Get daily returns for a specific ticker over the specified timeframe.

    Returns the decimal change in price from day to day (e.g., 0.015 = 1.5% gain).

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')
        years: Number of years of historical data (1-10, default 1)

    Returns:
        Daily returns data with:
        - ticker: Ticker symbol
        - returns: List of {date, return} objects (return is decimal: 0.015 = 1.5%)
        - startDate: Start date of the period
        - endDate: End date of the period
        - totalDataPoints: Number of data points

    Cache TTL: 1 day (86400s)
    Cache key pattern: ticker:returns:{ticker}:{years}
    """
    return await get_ticker_returns_controller(ticker=ticker, years=years)
