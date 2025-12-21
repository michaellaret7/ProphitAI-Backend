import asyncio
import hashlib
from fastapi import HTTPException
from typing import Optional, Dict, Any, List
from app.repositories.user_data import (
    get_user_watchlists,
    get_watchlist_by_id,
    add_watchlist,
    rename_watchlist,
    delete_watchlist,
    add_watchlist_item,
    delete_watchlist_item
)
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.redis.client import cache

def _format_watchlist_response(watchlist: dict) -> Dict[str, Any]:
    """Format a single watchlist for API response."""
    return {
        "id": watchlist.get("id"),
        "userId": watchlist.get("user_id"),
        "name": watchlist.get("name"),
        "creationDate": watchlist.get("creation_date"),
        "updatedDate": watchlist.get("updated_date"),
        "items": [
            {
                "ticker": item.get("ticker"),
                "priceOnInception": item.get("price_on_inception"),
                "addedAt": item.get("added_at"),
            }
            for item in watchlist.get("items", [])
        ],
    }


def _format_watchlist_item_response(item: dict) -> Dict[str, Any]:
    """Format a watchlist item for API response."""
    return {
        "watchlistId": item.get("watchlist_id"),
        "ticker": item.get("ticker"),
        "priceOnInception": item.get("price_on_inception"),
        "addedAt": item.get("added_at"),
    }


@handle_controller_errors
async def get_user_watchlists_controller(*, user_id: str) -> Dict[str, Any]:
    """Get all watchlists for a user."""
    if not user_id:
        raise ValueError("userId is required")

    watchlists = get_user_watchlists(user_id=user_id)

    return ok_envelope(
        message="Watchlists retrieved successfully",
        kind="watchlists#list",
        self_link=f"/api/watchlists",
        counts={"totalItems": len(watchlists)},
        payload=[_format_watchlist_response(w) for w in watchlists],
    )


@handle_controller_errors
async def get_watchlist_controller(*, watchlist_id: str, user_id: str) -> Dict[str, Any]:
    """Get a single watchlist by ID."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ok_envelope(
        message="Watchlist retrieved successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist.get("id"),
        self_link=f"/api/watchlists/{watchlist_id}",
        payload=_format_watchlist_response(watchlist),
    )


@handle_controller_errors
async def create_watchlist_controller(*, user_id: str, name: str) -> Dict[str, Any]:
    """Create a new watchlist for a user."""
    if not user_id:
        raise ValueError("userId is required")
    if not name:
        raise ValueError("name is required")

    watchlist = add_watchlist(user_id=user_id, name=name)

    return ok_envelope(
        message="Watchlist created successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist.get("id"),
        self_link=f"/api/watchlists/{watchlist.get('id')}",
        status=201,
        payload={
            "id": watchlist.get("id"),
            "userId": watchlist.get("user_id"),
            "name": watchlist.get("name"),
            "creationDate": watchlist.get("creation_date"),
        },
    )


@handle_controller_errors
async def rename_watchlist_controller(
    *, watchlist_id: str, user_id: str, name: str
) -> Dict[str, Any]:
    """Rename an existing watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not name:
        raise ValueError("name is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    result = rename_watchlist(watchlist_id=watchlist_id, name=name)

    return ok_envelope(
        message="Watchlist renamed successfully",
        kind="watchlists#watchlist",
        resource_id=result.get("id"),
        self_link=f"/api/watchlists/{watchlist_id}",
        payload={
            "id": result.get("id"),
            "name": result.get("name"),
            "updatedDate": result.get("updated_date"),
        },
    )


@handle_controller_errors
async def delete_watchlist_controller(*, watchlist_id: str, user_id: str) -> Dict[str, Any]:
    """Delete a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    delete_watchlist(watchlist_id=watchlist_id)

    return ok_envelope(
        message="Watchlist deleted successfully",
        kind="watchlists#watchlist",
        resource_id=watchlist_id,
        self_link=f"/api/watchlists/{watchlist_id}",
        payload={},
    )


@handle_controller_errors
async def add_watchlist_item_controller(
    *, watchlist_id: str, user_id: str, ticker: str
) -> Dict[str, Any]:
    """Add a ticker to a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not ticker:
        raise ValueError("ticker is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    item = add_watchlist_item(
        watchlist_id=watchlist_id,
        ticker=ticker
    )

    return ok_envelope(
        message="Ticker added to watchlist",
        kind="watchlists#item",
        self_link=f"/api/watchlists/{watchlist_id}/items/{item.get('ticker')}",
        status=201,
        payload=_format_watchlist_item_response(item),
    )


@handle_controller_errors
async def delete_watchlist_item_controller(
    *, watchlist_id: str, user_id: str, ticker: str
) -> Dict[str, Any]:
    """Remove a ticker from a watchlist."""
    if not watchlist_id:
        raise ValueError("watchlistId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not ticker:
        raise ValueError("ticker is required")

    watchlist = get_watchlist_by_id(watchlist_id=watchlist_id)

    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    if watchlist.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    deleted = delete_watchlist_item(watchlist_id=watchlist_id, ticker=ticker)

    if not deleted:
        raise HTTPException(status_code=404, detail="Ticker not found in watchlist")

    return ok_envelope(
        message="Ticker removed from watchlist",
        kind="watchlists#item",
        self_link=f"/api/watchlists/{watchlist_id}/items/{ticker}",
        payload={},
    )


def _safe_round(value: Any, decimals: int = 4) -> Any:
    """Safely round numeric values, returning None for non-numeric types."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(value, decimals)
    return value


def _build_metrics_for_ticker(
    ticker: str,
    quote_data: Dict[str, Any],
    ratios_data: Dict[str, Any],
    key_metrics_data: Dict[str, Any],
    price_change_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Build structured metrics response for a single ticker.

    Organizes FMP data into frontend-friendly categories matching UI tabs.
    """
    # Performance metrics (price change percentages)
    performance = {
        "1D": _safe_round(price_change_data.get("1D")),
        "5D": _safe_round(price_change_data.get("5D")),
        "1M": _safe_round(price_change_data.get("1M")),
        "3M": _safe_round(price_change_data.get("3M")),
        "6M": _safe_round(price_change_data.get("6M")),
        "ytd": _safe_round(price_change_data.get("ytd")),
        "1Y": _safe_round(price_change_data.get("1Y")),
        "3Y": _safe_round(price_change_data.get("3Y")),
        "5Y": _safe_round(price_change_data.get("5Y")),
    }

    # Valuation metrics
    valuation = {
        "price": _safe_round(quote_data.get("price"), 2),
        "marketCap": quote_data.get("marketCap"),
        "divYield": _safe_round(ratios_data.get("dividendYielTTM")),
        "pe": _safe_round(ratios_data.get("peRatioTTM"), 2),
        "peg": _safe_round(ratios_data.get("pegRatioTTM"), 2),
        "pb": _safe_round(ratios_data.get("priceToBookRatioTTM"), 2),
        "pSales": _safe_round(ratios_data.get("priceToSalesRatioTTM"), 2),
        "pFcf": _safe_round(ratios_data.get("priceToFreeCashFlowsRatioTTM"), 2),
        "pOcf": _safe_round(ratios_data.get("priceToOperatingCashFlowsRatioTTM"), 2),
        "evEbitda": _safe_round(ratios_data.get("enterpriseValueMultipleTTM"), 2),
        "payout": _safe_round(ratios_data.get("payoutRatioTTM")),
    }

    # Profitability metrics
    profitability = {
        "grossMargin": _safe_round(ratios_data.get("grossProfitMarginTTM")),
        "opMargin": _safe_round(ratios_data.get("operatingProfitMarginTTM")),
        "pretaxMargin": _safe_round(ratios_data.get("pretaxProfitMarginTTM")),
        "netMargin": _safe_round(ratios_data.get("netProfitMarginTTM")),
        "effTaxRate": _safe_round(ratios_data.get("effectiveTaxRateTTM")),
        "roa": _safe_round(ratios_data.get("returnOnAssetsTTM")),
        "roe": _safe_round(ratios_data.get("returnOnEquityTTM")),
        "roce": _safe_round(ratios_data.get("returnOnCapitalEmployedTTM")),
        # NI/EBT approximation: 1 - effective tax rate
        "niEbt": _safe_round(1 - ratios_data.get("effectiveTaxRateTTM", 0)) if ratios_data.get("effectiveTaxRateTTM") is not None else None,
        # EBT/EBIT: Use ebtPerEbitTTM if available, otherwise approximate
        "ebtEbit": _safe_round(ratios_data.get("ebtPerEbitTTM")),
    }

    # Cash Flow & Leverage metrics
    cash_flow_leverage = {
        "ocfPerShare": _safe_round(key_metrics_data.get("operatingCashFlowPerShareTTM"), 2),
        "fcfPerShare": _safe_round(key_metrics_data.get("freeCashFlowPerShareTTM"), 2),
        "cashPerShare": _safe_round(key_metrics_data.get("cashPerShareTTM"), 2),
        "ocfSales": _safe_round(ratios_data.get("operatingCashFlowSalesRatioTTM")),
        "fcfOcf": _safe_round(ratios_data.get("freeCashFlowOperatingCashFlowRatioTTM")),
        "capexCov": _safe_round(ratios_data.get("capitalExpenditureCoverageRatioTTM"), 2),
        # Div+CapEx Coverage: Use dividendPaidAndCapexCoverageRatioTTM
        "divCapexCov": _safe_round(ratios_data.get("dividendPaidAndCapexCoverageRatioTTM"), 2),
        "debtRatio": _safe_round(ratios_data.get("debtRatioTTM")),
        "de": _safe_round(ratios_data.get("debtEquityRatioTTM"), 2),
        "ltDebtCap": _safe_round(ratios_data.get("longTermDebtToCapitalizationTTM")),
        "debtCap": _safe_round(ratios_data.get("totalDebtToCapitalizationTTM")),
        "intCov": _safe_round(ratios_data.get("interestCoverageTTM"), 2),
    }

    # Operating Metrics
    operating_metrics = {
        "currentRatio": _safe_round(ratios_data.get("currentRatioTTM"), 2),
        "quickRatio": _safe_round(ratios_data.get("quickRatioTTM"), 2),
        "cashRatio": _safe_round(ratios_data.get("cashRatioTTM"), 2),
        "dso": _safe_round(ratios_data.get("daysOfSalesOutstandingTTM"), 2),
        "dio": _safe_round(ratios_data.get("daysOfInventoryOutstandingTTM"), 2),
        "opCycle": _safe_round(ratios_data.get("operatingCycleTTM"), 2),
        "dpo": _safe_round(ratios_data.get("daysOfPayablesOutstandingTTM"), 2),
        "ccc": _safe_round(ratios_data.get("cashConversionCycleTTM"), 2),
        "recvTurn": _safe_round(ratios_data.get("receivablesTurnoverTTM"), 2),
        "payTurn": _safe_round(ratios_data.get("payablesTurnoverTTM"), 2),
        "invTurn": _safe_round(ratios_data.get("inventoryTurnoverTTM"), 2),
        "faTurn": _safe_round(ratios_data.get("fixedAssetTurnoverTTM"), 2),
        "assetTurn": _safe_round(ratios_data.get("assetTurnoverTTM"), 2),
    }

    return {
        "ticker": ticker,
        "name": quote_data.get("name", ""),
        "performance": performance,
        "valuation": valuation,
        "profitability": profitability,
        "cashFlowLeverage": cash_flow_leverage,
        "operatingMetrics": operating_metrics,
    }


@handle_controller_errors
async def get_watchlist_metrics_controller(
    *,
    tickers: List[str],
) -> Dict[str, Any]:
    """Get all financial metrics for a list of tickers.

    Fetches TTM ratios, key metrics, quotes, and price changes in parallel
    to provide all data needed for watchlist metrics tables.

    Cache TTL: 5 minutes (300s) - balances freshness with API rate limits.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        Response envelope with metrics organized by ticker and category
    """
    if not tickers:
        raise ValueError("tickers list cannot be empty")

    # Normalize tickers to uppercase and deduplicate
    tickers = list(set(t.upper() for t in tickers))

    # Generate cache key from sorted tickers using deterministic hash
    sorted_tickers = sorted(tickers)
    tickers_hash = hashlib.md5(",".join(sorted_tickers).encode()).hexdigest()[:16]
    cache_key = f"watchlist:metrics:{tickers_hash}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    fmp = FMP_API_DATA()

    # Fetch batch quote for all tickers at once
    batch_quotes = await asyncio.to_thread(fmp.get_batch_quote, tickers)
    quote_map = {}
    if batch_quotes:
        for quote in batch_quotes:
            symbol = quote.get("symbol")
            if symbol:
                quote_map[symbol] = quote

    # Define async fetchers for per-ticker data
    async def fetch_ratios(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_ratios_ttm, ticker)

    async def fetch_key_metrics(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_key_metrics_ttm, ticker)

    async def fetch_price_change(ticker: str):
        return ticker, await asyncio.to_thread(fmp.get_stock_price_change, ticker)

    # Fetch all data in parallel
    ratios_results, metrics_results, price_results = await asyncio.gather(
        asyncio.gather(*[fetch_ratios(t) for t in tickers], return_exceptions=True),
        asyncio.gather(*[fetch_key_metrics(t) for t in tickers], return_exceptions=True),
        asyncio.gather(*[fetch_price_change(t) for t in tickers], return_exceptions=True),
    )

    # Process results into maps
    ratios_map = {}
    for result in ratios_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            ratios_map[ticker] = data[0]
        else:
            ratios_map[ticker] = {}

    metrics_map = {}
    for result in metrics_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            metrics_map[ticker] = data[0]
        else:
            metrics_map[ticker] = {}

    price_change_map = {}
    for result in price_results:
        if isinstance(result, Exception):
            continue
        ticker, data = result
        if data and isinstance(data, list) and len(data) > 0:
            price_change_map[ticker] = data[0]
        else:
            price_change_map[ticker] = {}

    # Build response for each ticker
    payload = {}
    errors = []

    for ticker in tickers:
        quote_data = quote_map.get(ticker, {})
        ratios_data = ratios_map.get(ticker, {})
        key_metrics_data = metrics_map.get(ticker, {})
        price_change_data = price_change_map.get(ticker, {})

        # Check if we have any data for this ticker
        if not quote_data and not ratios_data:
            errors.append(ticker)
            continue

        payload[ticker] = _build_metrics_for_ticker(
            ticker=ticker,
            quote_data=quote_data,
            ratios_data=ratios_data,
            key_metrics_data=key_metrics_data,
            price_change_data=price_change_data,
        )

    # Build response envelope
    response = ok_envelope(
        message=f"Watchlist metrics retrieved successfully ({len(payload)} tickers)",
        kind="watchlists#metrics",
        self_link="/api/watchlists/metrics",
        counts={"totalItems": len(payload), "errors": len(errors)},
        payload={
            "data": payload,
            "errors": errors if errors else None,
        },
    )

    # Cache for 5 minutes
    await cache.set(cache_key, response, ttl=300)

    return response
