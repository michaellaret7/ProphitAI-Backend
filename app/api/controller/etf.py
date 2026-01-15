"""Controllers for ETF endpoints."""

import asyncio
from typing import Dict, Any, List

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.etfs.info import ETFInfoService
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.services.etfs.holdings import ETFHoldingsService
from app.services.etfs.countries import ETFCountryWeightingsService


@handle_controller_errors
async def get_etf_info_controller(*, symbol: str) -> Dict[str, Any]:
    """
    Get ETF information and metadata.

    Cache TTL: 1 day (86400s) for ETF info

    Args:
        symbol: ETF ticker symbol (e.g., "SPY", "QQQ")

    Returns:
        Response envelope with ETF info
    """
    # Generate cache key
    cache_key = f"etf:info:{symbol}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch ETF info
    service = ETFInfoService(symbol=symbol)
    data = service.get_info()

    # Build response envelope
    response = ok_envelope(
        message="ETF information retrieved successfully",
        kind="etf#info",
        resource_id=symbol,
        self_link=f"/api/etf/{symbol}/info",
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_etf_holdings_controller(*, symbol: str) -> Dict[str, Any]:
    """
    Get ETF holdings data.

    Cache TTL: 1 day (86400s) for holdings

    Args:
        symbol: ETF ticker symbol (e.g., "SPY", "QQQ")

    Returns:
        Response envelope with ETF holdings
    """
    # Generate cache key
    cache_key = f"etf:holdings:{symbol}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch ETF holdings
    service = ETFHoldingsService(symbol=symbol)
    data = service.get_holdings()

    # Build response envelope
    response = ok_envelope(
        message="ETF holdings retrieved successfully",
        kind="etf#holdings",
        resource_id=symbol,
        self_link=f"/api/etf/{symbol}/holdings",
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_etf_country_weightings_controller(*, symbol: str) -> Dict[str, Any]:
    """
    Get ETF country weightings data.

    Cache TTL: 1 day (86400s) for country weightings

    Args:
        symbol: ETF ticker symbol (e.g., "SPY", "QQQ")

    Returns:
        Response envelope with ETF country weightings
    """
    # Generate cache key
    cache_key = f"etf:countries:{symbol}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch ETF country weightings
    service = ETFCountryWeightingsService(symbol=symbol)
    data = service.get_country_weightings()

    # Build response envelope
    response = ok_envelope(
        message="ETF country weightings retrieved successfully",
        kind="etf#countryWeightings",
        resource_id=symbol,
        self_link=f"/api/etf/{symbol}/countries",
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_batch_etf_info_controller(symbols: List[str]) -> Dict[str, Any]:
    """
    Retrieve ETF information for multiple symbols in a single request.

    Parallelizes FMP API calls using asyncio.gather since there's no native
    batch endpoint for ETF info.

    Cache TTL: 1 day (86400s)
    Cache key pattern: etf:info:batch:{sorted_symbols_hash}

    Args:
        symbols: List of ETF symbols (max 10)

    Returns:
        Response envelope with batch ETF info payload
    """
    # Generate cache key from sorted symbols for consistent caching
    sorted_symbols = sorted(symbols)
    cache_key = f"etf:info:batch:{hash(tuple(sorted_symbols))}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch from FMP API in parallel
    fmp = FMP_API_DATA()

    async def fetch_etf_info(symbol: str) -> tuple[str, Dict[str, Any] | None]:
        """Helper to fetch single ETF info with error handling."""
        try:
            raw_data = await asyncio.to_thread(fmp.get_etf_info, symbol)
            if raw_data and isinstance(raw_data, list) and len(raw_data) > 0:
                # Reason: FMP returns list with single ETF info object
                data = raw_data[0]
                # Remove internal fields
                return symbol, {k: v for k, v in data.items() if k != "updatedAt"}
            return symbol, None
        except Exception:
            return symbol, None

    # Run all FMP API calls concurrently
    results = await asyncio.gather(
        *[fetch_etf_info(symbol) for symbol in symbols],
        return_exceptions=True
    )

    # Process results
    etf_data_map: Dict[str, Dict[str, Any]] = {}
    missing_symbols: List[str] = []

    for result in results:
        # Skip failed requests (exceptions)
        if isinstance(result, Exception):
            continue

        symbol, data = result
        if data:
            etf_data_map[symbol] = data
        else:
            missing_symbols.append(symbol)

    # Build response envelope
    response = ok_envelope(
        message=f"Batch ETF info retrieved successfully ({len(etf_data_map)} found, {len(missing_symbols)} not found)",
        kind="etf#batchInfo",
        resource_id=",".join(sorted_symbols),
        self_link="/api/etf/info/batch",
        counts={
            "totalRequested": len(symbols),
            "found": len(etf_data_map),
            "notFound": len(missing_symbols)
        },
        payload={
            "data": etf_data_map,
            "missing_symbols": missing_symbols
        },
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response
