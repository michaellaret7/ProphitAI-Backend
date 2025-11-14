"""
Ticker-specific API endpoints.

Provides access to fundamental financial data for individual tickers.
"""

from fastapi import APIRouter, Query

from app.api.controller.ticker import get_ticker_fundamentals_controller

router = APIRouter(tags=["Ticker Data 🎯"])


@router.get("/ticker/fundamentals")
async def get_ticker_fundamentals(
    ticker: str = Query(
        ...,
        description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')",
        min_length=1,
        max_length=10,
    ),
    quarters_back: int = Query(
        4,
        alias="quartersBack",
        description="Number of historical quarters to return (max 32 quarters = 8 years)",
        ge=1,
        le=32,
    ),
):
    """
    Get all fundamental financial data for a ticker.

    Returns:
    - Income statements
    - Balance sheets
    - Cash flow statements
    - Financial ratios

    Example: GET /api/ticker/fundamentals?ticker=AAPL&quartersBack=4
    """
    return await get_ticker_fundamentals_controller(
        ticker=ticker,
        quarters_back=quarters_back,
    )
