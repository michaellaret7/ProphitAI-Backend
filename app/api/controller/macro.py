"""Controllers for macro data endpoints."""

import asyncio
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.macro.macro_service import (
    CommodityPriceService,
    GovernmentBondRatesService,
    EconomicIndicatorService,
    EconomicCalendarService,
)
from app.services.macro.sector_service import (
    SectorPerformanceService,
    SectorPEService,
    IndustryPerformanceService,
    IndustryPEService,
)
from app.db.core.pull_fmp_data import FMP_API_DATA

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

@handle_controller_errors
async def get_sector_performance_controller(
    *,
    sector: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get historical sector performance data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        sector: Sector name (e.g., "Technology", "Healthcare")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with sector performance data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:sector:performance:{sector}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch sector performance
    service = SectorPerformanceService(
        sector=sector,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_performance)

    # Build response envelope
    response = ok_envelope(
        message="Sector performance data retrieved successfully",
        kind="macro#sectorPerformance",
        resource_id=sector,
        self_link=f"/api/macro/sector/performance?sector={sector}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_sector_pe_controller(
    *,
    sector: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get historical sector P/E ratio data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        sector: Sector name (e.g., "Technology", "Healthcare")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with sector P/E data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:sector:pe:{sector}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch sector P/E data
    service = SectorPEService(
        sector=sector,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_pe_ratios)

    # Build response envelope
    response = ok_envelope(
        message="Sector P/E data retrieved successfully",
        kind="macro#sectorPE",
        resource_id=sector,
        self_link=f"/api/macro/sector/pe?sector={sector}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_industry_performance_controller(
    *,
    industry: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get historical industry performance data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        industry: Industry name (e.g., "Software", "Biotechnology")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with industry performance data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:industry:performance:{industry}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch industry performance
    service = IndustryPerformanceService(
        industry=industry,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_performance)

    # Build response envelope
    response = ok_envelope(
        message="Industry performance data retrieved successfully",
        kind="macro#industryPerformance",
        resource_id=industry,
        self_link=f"/api/macro/industry/performance?industry={industry}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_industry_pe_controller(
    *,
    industry: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get historical industry P/E ratio data.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        industry: Industry name (e.g., "Software", "Biotechnology")
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        Response envelope with industry P/E data
    """
    # Generate cache key
    start_key = start_date or "all"
    end_key = end_date or "all"
    cache_key = f"macro:industry:pe:{industry}:{start_key}:{end_key}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - fetch industry P/E data
    service = IndustryPEService(
        industry=industry,
        start_date=start_date,
        end_date=end_date,
    )
    # Reason: Run blocking DB query + data processing in thread pool to prevent event loop blocking
    data = await asyncio.to_thread(service.get_pe_ratios)

    # Build response envelope
    response = ok_envelope(
        message="Industry P/E data retrieved successfully",
        kind="macro#industryPE",
        resource_id=industry,
        self_link=f"/api/macro/industry/pe?industry={industry}"
        + (f"&startDate={start_date}" if start_date else "")
        + (f"&endDate={end_date}" if end_date else ""),
        counts=data["counts"],
        payload=data["payload"],
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_mergers_acquisitions_latest_controller(
    page: int = 0,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Controller to handle latest M&A data retrieval
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    # FMP API uses requests.get() which is synchronous and blocks during network I/O
    data = await asyncio.to_thread(fmp_api.get_mergers_acquisitions_latest, page=page, limit=limit)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve M&A data from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Latest M&A transactions retrieved successfully",
        kind="macro#mergersAcquisitionsLatest",
        self_link=f"/api/macro/mergers-acquisitions/latest?page={page}&limit={limit}",
        counts={"totalItems": len(items), "currentItemCount": len(items), "startIndex": page * limit},
        payload=items,
    )


@handle_controller_errors
async def get_mergers_acquisitions_search_controller(
    name: str,
) -> Dict[str, Any]:
    """
    Controller to handle M&A search by company name
    """
    fmp_api = FMP_API_DATA()
    # Reason: Run blocking HTTP request in thread pool to prevent event loop blocking
    # FMP API uses requests.get() which is synchronous and blocks during network I/O
    data = await asyncio.to_thread(fmp_api.get_mergers_acquisitions_search, name=name)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve M&A data from FMP API")

    # Convert to list if not already
    items = data if isinstance(data, list) else []

    return ok_envelope(
        message=f"M&A transactions for '{name}' retrieved successfully",
        kind="macro#mergersAcquisitionsSearch",
        resource_id=name,
        self_link=f"/api/macro/mergers-acquisitions/search?name={name}",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )

async def get_fx_historical_prices_controller(
    pair: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Controller to handle FX historical prices retrieval
    """
    fmp_api = FMP_API_DATA()
    data = await asyncio.to_thread(fmp_api.get_forex_historical_prices, pair=pair, from_date=from_date, to_date=to_date)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve FX historical prices from FMP API")

    return ok_envelope(
        message="FX historical prices retrieved successfully",
        kind="macro#fxHistoricalPrices",
        resource_id=pair,
        self_link=f"/api/macro/fx/historical-prices?pair={pair}&fromDate={from_date}&endDate={to_date}",
        counts={"totalItems": len(data["historical"]), "currentItemCount": len(data["historical"])},
        payload=data["historical"],
    )


@handle_controller_errors
async def get_index_list_controller() -> Dict[str, Any]:
    """
    Controller to retrieve list of all available market indexes.

    Returns:
        Response envelope with list of indexes (symbol, name, exchange, currency)
    """
    fmp_api = FMP_API_DATA()
    data = await asyncio.to_thread(fmp_api.get_index_list)

    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve index list from FMP API")

    items = data if isinstance(data, list) else []

    return ok_envelope(
        message="Index list retrieved successfully",
        kind="macro#indexList",
        resource_id="all",
        self_link="/api/macro/index/list",
        counts={"totalItems": len(items), "currentItemCount": len(items)},
        payload=items,
    )


