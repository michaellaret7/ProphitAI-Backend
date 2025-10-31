from fastapi import APIRouter, Query, Depends
from typing import List
from app.api.controller.price import get_stock_prices_controller
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
