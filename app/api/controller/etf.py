"""Controllers for ETF endpoints."""

from typing import Dict, Any

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.etfs.info import ETFInfoService
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
