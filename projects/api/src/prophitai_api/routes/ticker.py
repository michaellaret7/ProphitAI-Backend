"""
Ticker-specific API endpoints.

Provides access to fundamental financial data for individual tickers.
"""

from fastapi import APIRouter, Query, Depends
from typing import List

from prophitai_api.controllers.ticker import (
    get_ticker_fundamentals_controller,
    get_ticker_info_controller,
    get_batch_ticker_info_controller,
    get_ttm_ratios_for_ticker_comps_controller,
)
from prophitai_api.schemas.ticker import BatchTickerInfoRequest, TTMRatiosTickerCompsRequest

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
    - Market data: avg_volume, dollar_volume
    - Valuation: eps, beta
    - Status: is_etf, is_actively_trading, is_adr, is_fund
    - Other: ipo_date, earnings_announcement, shares_outstanding

    For real-time price, market_cap, and PE ratio, use GET /api/price/quote

    Example: GET /api/ticker/info?ticker=AAPL
    """
    return await get_ticker_info_controller(ticker=ticker)


@router.post("/ticker/info/batch")
async def get_batch_ticker_info(body: BatchTickerInfoRequest):
    """
    Get basic ticker information for multiple tickers in a single request.

    Optimized batch endpoint that reduces database overhead by fetching all tickers
    in one query and parallelizing FMP API calls for company profiles.

    Returns a dictionary mapping each ticker to its info, plus a list of any
    tickers that were not found in the database.

    Response payload structure:
    - data: Dictionary mapping ticker -> ticker info
    - missing_tickers: List of tickers not found

    Cache TTL: 1 day (86400s)

    Example request body:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL", "INVALID_TICKER"]
    }

    Example response payload:
    {
        "data": {
            "AAPL": {...ticker info...},
            "MSFT": {...ticker info...},
            "GOOGL": {...ticker info...}
        },
        "missing_tickers": ["INVALID_TICKER"]
    }
    """
    return await get_batch_ticker_info_controller(tickers=body.tickers)


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
