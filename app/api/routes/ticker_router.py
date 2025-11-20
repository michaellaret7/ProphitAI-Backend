"""
Ticker-specific API endpoints.

Provides access to fundamental financial data for individual tickers.
"""

from fastapi import APIRouter, Query, Depends
from typing import List

from app.api.controller.ticker import (
    get_ticker_fundamentals_controller,
    get_ticker_info_controller,
    get_ttm_ratios_for_ticker_comps_controller,
)
from app.models.ticker_models import TTMRatiosTickerCompsRequest

router = APIRouter(tags=["Ticker Data 🎯"])


@router.get("/ticker/info")
async def get_ticker_info(
    ticker: str = Query(
        ...,
        description="Stock ticker symbol (e.g., 'AAPL', 'MSFT')",
        min_length=1,
        max_length=10,
    ),
):
    """
    Get basic ticker information and metadata.

    Returns comprehensive ticker details including:
    - Basic info: ticker symbol, sector, industry, sub_industry
    - Market data: price, market_cap, avg_volume, dollar_volume
    - Valuation: eps, pe ratio, beta
    - Status: is_etf, is_actively_trading, is_adr, is_fund
    - Other: ipo_date, earnings_announcement, shares_outstanding

    Example: GET /api/ticker/info?ticker=AAPL
    """
    return await get_ticker_info_controller(ticker=ticker)


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


def parse_ttm_ratios_ticker_comps_request(
    tickers: List[str] = Query(
        ...,
        description="Comma-separated list of stock ticker symbols (e.g., 'AAPL,MSFT,GOOGL')",
        min_length=1,
        max_length=50,
    ),
) -> TTMRatiosTickerCompsRequest:
    """Parse and validate parameters into TTMRatiosTickerCompsRequest model"""
    return TTMRatiosTickerCompsRequest(tickers=tickers)


@router.get("/ticker/ttm-ratios-for-ticker-comps")
async def get_ttm_ratios_for_ticker_comps(
    request: TTMRatiosTickerCompsRequest = Depends(parse_ttm_ratios_ticker_comps_request)
):
    """
    Get trailing twelve months (TTM) financial ratios for multiple tickers (comparables).

    This endpoint allows you to fetch TTM ratios for multiple companies at once,
    making it ideal for comparative analysis across peer groups or industries.

    Args:
        tickers: List of stock ticker symbols (max 50)

    Returns:
        Dictionary mapping each ticker to its TTM financial ratios including:
        - Profitability: ROE, ROA, net profit margin, gross profit margin, operating margin
        - Valuation: P/E ratio, P/B ratio, price to sales, EV/EBITDA
        - Leverage: Debt to equity, debt to assets, interest coverage
        - Liquidity: Current ratio, quick ratio, cash ratio
        - Efficiency: Asset turnover, inventory turnover, receivables turnover

    Example: GET /api/ticker/ttm-ratios-for-ticker-comps?tickers=AAPL&tickers=MSFT&tickers=GOOGL
    """
    return await get_ttm_ratios_for_ticker_comps_controller(tickers=request.tickers)
