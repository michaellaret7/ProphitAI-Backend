"""Controllers for economic data endpoints (commodities, bonds, indicators, calendar)."""

import asyncio
from typing import Dict, Any, Optional

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.macro.macro_service import (
    CommodityPriceService,
    GovernmentBondRatesService,
    EconomicIndicatorService,
    EconomicCalendarService,
)


@handle_controller_errors
async def get_commodity_prices_controller(
    *,
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get commodity OHLCV price data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        symbol: Commodity symbol (e.g., "GCUSD" for gold)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with commodity price data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:commodity:{symbol}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch commodity prices
    service = CommodityPriceService(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_prices)

    # Build response envelope
    response = ok_envelope(
        message="Commodity price data retrieved successfully",
        kind="macro#commodityPrices",
        resource_id=symbol,
        self_link=f"/api/macro/commodities?symbol={symbol}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_bond_rates_controller(
    *,
    country: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get government bond rates (yield curve) data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        country: Country code - 2-letter (e.g., "ES" for Spain) or 3-letter (e.g., "USA" for United States)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with bond rates data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:rates:{country}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch bond rates
    service = GovernmentBondRatesService(
        country=country,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    # This prevents the API from freezing when processing large datasets (8,970+ rows with 13 fields each)
    data = await asyncio.to_thread(service.get_rates)

    # Build response envelope
    response = ok_envelope(
        message="Government bond rates retrieved successfully",
        kind="macro#bondRates",
        resource_id=country,
        self_link=f"/api/macro/rates?country={country}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_economic_indicator_controller(
    *,
    indicator: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get economic indicator time series data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        indicator: Indicator name (e.g., "GDP", "CPI", "unemployment_rate")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with economic indicator data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:indicator:{indicator}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch indicator data
    service = EconomicIndicatorService(
        indicator=indicator,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_indicator_data)

    # Build response envelope
    response = ok_envelope(
        message="Economic indicator data retrieved successfully",
        kind="macro#economicIndicator",
        resource_id=indicator,
        self_link=f"/api/macro/indicators?indicator={indicator}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_economic_calendar_controller(
    *,
    country: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get economic calendar events for a country.

    Cache TTL: 1 hour (3600s) for calendar data (updates more frequently)

    Args:
        country: Country code (e.g., "US", "UK", "CA", "FR", "DE", "IT", "JP")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)
        event: Event name filter - partial match, case-insensitive (optional)

    Returns:
        Response envelope with economic calendar events
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    event_key = event.replace(" ", "_") if event else "all"
    cache_key = f"macro:calendar:{country}:{start_key}:{end_key}:{event_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch calendar events
    service = EconomicCalendarService(
        country=country,
        start_date=start_date,
        end_date=end_date,
        event=event,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_calendar_events)

    # Build response envelope
    response = ok_envelope(
        message="Economic calendar events retrieved successfully",
        kind="macro#economicCalendar",
        resource_id=country,
        self_link=f"/api/macro/calendar?country={country}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else "")
        + (f"&event={event}" if event else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 hour (calendar data updates more frequently than other macro data)
    await cache.set(cache_key, response, ttl=3600)

    return response
