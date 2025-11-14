"""
Ticker-specific data controller.

Handles fetching fundamental financial data (income statements, balance sheets,
cash flow statements, and financial ratios) for individual tickers.
"""

from typing import Any, Dict

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.repositories.fundamental_data import get_all_columns_fundamentals
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from fastapi import HTTPException
from app.utils.serialize_output import serialize_sqlalchemy_obj


@handle_controller_errors
async def get_ticker_info_controller(
    *,
    ticker: str,
) -> Dict[str, Any]:
    """
    Retrieve basic ticker information and metadata.

    Returns ticker details including price, market cap, sector, industry,
    beta, and other key metrics from the tickers table.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Response envelope with ticker info payload
    """
    with MarketSession() as session:
        ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()

        if not ticker_obj:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker.upper()} not found")

        response = ok_envelope(
            message=f"Ticker info for {ticker.upper()} retrieved successfully",
            kind="ticker#info",
            resource_id=ticker.upper(),
            self_link=f"/api/ticker/info?ticker={ticker.upper()}",
            payload=serialize_sqlalchemy_obj(ticker_obj),
        )
    return response

    
@handle_controller_errors
async def get_ticker_fundamentals_controller(
    *,
    ticker: str,
    quarters_back: int = 4,
) -> Dict[str, Any]:
    """
    Retrieve all fundamental financial data for a ticker (full column payloads).

    Returns income statements, balance sheets, cash flow statements,
    financial ratios, and analyst estimates in a single response, using
    all available fields from the database for each statement type.

    Cache TTL: 1 day (86400s)

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        quarters_back: Number of historical quarters to return (default: 4)

    Returns:
        Response envelope with fundamental data payload
    """
    # Generate cache key
    cache_key = f"ticker:fundamentals:{ticker.upper()}:{quarters_back}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch from database (full columns for each statement type)
    statement_types = [
        "income_statement",
        "balance_sheet",
        "cash_flow",
        "financial_ratios",
        "analyst_estimates",
    ]

    fundamentals: Dict[str, Any] = {
        "ticker": ticker.upper(),
        "quarters_requested": quarters_back,
    }
    for stype in statement_types:
        data = get_all_columns_fundamentals(
            ticker=ticker,
            statement_type=stype,
            quarters_back=quarters_back,
        )
        fundamentals[stype] = data.get("data") if isinstance(data, dict) and "error" not in data else {"error": data.get("error", "Unknown error")}

    # Build response envelope
    response = ok_envelope(
        message=f"Fundamental data for {ticker.upper()} retrieved successfully",
        kind="ticker#fundamentals",
        resource_id=ticker.upper(),
        self_link=f"/api/ticker/fundamentals?ticker={ticker.upper()}&quartersBack={quarters_back}",
        payload=fundamentals,
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response
