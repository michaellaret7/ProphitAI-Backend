"""
Ticker-specific data controller.

Handles fetching fundamental financial data (income statements, balance sheets,
cash flow statements, and financial ratios) for individual tickers.
"""

import asyncio
from typing import Any, Dict

from app.api.response_envelope import ok_envelope
from app.db.core.pull_fmp_data import FMP_API_DATA
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

    Returns ticker details including sector, industry, beta, and other
    key metrics from the tickers table. For price data, use /price/quote.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')

    Returns:
        Response envelope with ticker info payload
    """
    # Reason: Query database first and close session immediately to prevent connection pool exhaustion
    with MarketSession() as session:
        ticker_obj = (
            session.query(Ticker)
            .filter(Ticker.ticker == ticker.upper())
            .first()
        )

        if not ticker_obj:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker.upper()} not found")

        # Serialize data while session is still active
        data = serialize_sqlalchemy_obj(ticker_obj)

    # Session is now closed - safe to make external API calls
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    company_profile = await asyncio.to_thread(fmp_api.get_company_profile, ticker.upper())

    # Add description from FMP
    if company_profile and isinstance(company_profile, list) and len(company_profile) > 0:
        data["description"] = company_profile[0].get("description", "")

    # Remove price-related fields (use /price/quote endpoint instead)
    for field in ["price", "pe", "market_cap"]:
        data.pop(field, None)

    response = ok_envelope(
        message=f"Ticker info for {ticker.upper()} retrieved successfully",
        kind="ticker#info",
        resource_id=ticker.upper(),
        self_link=f"/api/ticker/info?ticker={ticker.upper()}",
        payload=data,
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


# Duplicate TTM ratio fields to remove (keeping cleaner named versions)
TTM_RATIO_FIELDS_TO_REMOVE = [
    "priceEarningsRatioTTM",          # duplicate of peRatioTTM
    "priceBookValueRatioTTM",         # duplicate of priceToBookRatioTTM
    "priceFairValueTTM",              # duplicate
    "priceSalesRatioTTM",             # duplicate of priceToSalesRatioTTM
    "priceCashFlowRatioTTM",          # duplicate of priceToOperatingCashFlowsRatioTTM
    "ebitPerRevenueTTM",              # duplicate of operatingProfitMarginTTM
    "cashFlowCoverageRatiosTTM",      # duplicate of cashFlowToDebtRatioTTM
    "dividendYielPercentageTTM",      # duplicate of dividendYielTTM (just * 100)
    "priceEarningsToGrowthRatioTTM",  # duplicate of pegRatioTTM
]


@handle_controller_errors
async def get_batch_ticker_info_controller(
    tickers: list[str],
) -> Dict[str, Any]:
    """
    Retrieve basic ticker information for multiple tickers in a single request.

    Optimized batch endpoint that:
    - Fetches all ticker data in one DB query using .in_() filter
    - Parallelizes FMP API calls for company profiles
    - Returns a dictionary mapping ticker -> info

    Cache TTL: 1 day (86400s)
    Cache key pattern: ticker:info:batch:{sorted_tickers_hash}

    Args:
        tickers: List of stock ticker symbols (max 50, deduplicated)

    Returns:
        Response envelope with batch ticker info payload as dict
    """
    # Generate cache key from sorted tickers for consistent caching
    sorted_tickers = sorted(tickers)
    cache_key = f"ticker:info:batch:{hash(tuple(sorted_tickers))}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch from database using .in_() filter (1 query for all tickers)
    with MarketSession() as session:
        ticker_objs = (
            session.query(Ticker)
            .filter(Ticker.ticker.in_(tickers))
            .all()
        )

        # Serialize data while session is still active
        ticker_data_map = {
            obj.ticker: serialize_sqlalchemy_obj(obj)
            for obj in ticker_objs
        }

    # Identify found vs missing tickers
    found_tickers = set(ticker_data_map.keys())
    missing_tickers = set(tickers) - found_tickers

    # Session is now closed - safe to make external API calls
    fmp_api = FMP_API_DATA()

    # Fetch company profiles in parallel using asyncio.gather
    async def fetch_profile(ticker: str):
        """Helper to fetch single company profile"""
        return ticker, await asyncio.to_thread(fmp_api.get_company_profile, ticker)

    # Run all FMP API calls concurrently
    profile_results = await asyncio.gather(
        *[fetch_profile(ticker) for ticker in found_tickers],
        return_exceptions=True
    )

    # Process profile results and add descriptions
    for result in profile_results:
        # Skip failed requests (exceptions)
        if isinstance(result, Exception):
            continue

        ticker, profile = result
        if profile and isinstance(profile, list) and len(profile) > 0:
            ticker_data_map[ticker]["description"] = profile[0].get("description", "")

    # Remove price-related fields from all tickers (use /price/quote endpoint instead)
    for ticker_data in ticker_data_map.values():
        for field in ["price", "pe", "market_cap"]:
            ticker_data.pop(field, None)

    # Build response envelope
    response = ok_envelope(
        message=f"Batch ticker info retrieved successfully ({len(found_tickers)} found, {len(missing_tickers)} not found)",
        kind="ticker#batchInfo",
        resource_id=",".join(sorted_tickers),
        self_link=f"/api/ticker/info/batch",
        counts={"totalRequested": len(tickers), "found": len(found_tickers), "notFound": len(missing_tickers)},
        payload={
            "data": ticker_data_map,
            "missing_tickers": list(missing_tickers)
        },
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_ttm_ratios_for_ticker_comps_controller(
    tickers: list[str],
) -> Dict[str, Any]:
    """
    Retrieve TTM ratios for a list of tickers
    """
    fmp = FMP_API_DATA()

    # Fetch all tickers in parallel
    async def fetch_ratios(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_ratios_ttm, ticker)

    results = await asyncio.gather(*[fetch_ratios(t) for t in tickers], return_exceptions=True)

    data = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        ticker, raw_data = result
        # Remove duplicate fields
        if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
            cleaned = {k: v for k, v in raw_data[0].items() if k not in TTM_RATIO_FIELDS_TO_REMOVE}
            data[ticker] = cleaned
        else:
            data[ticker] = raw_data

    if not data:
        return ok_envelope(
            message=f"No TTM ratios found for ticker comps {tickers}",
            kind="ticker#ttmRatiosForTickerComps",
            resource_id=tickers,
            self_link=f"/api/ticker/ttm-ratios-for-ticker-comps?tickers={tickers}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )
    
    return ok_envelope(
        message="TTM ratios for ticker comps retrieved successfully",
        kind="ticker#ttmRatiosForTickerComps",
        resource_id=tickers,
        self_link=f"/api/ticker/ttm-ratios-for-ticker-comps?tickers={tickers}",
        counts={"totalItems": len(data) if isinstance(data, list) else 0, "currentItemCount": len(data) if isinstance(data, list) else 0},
        payload=data,
    )

