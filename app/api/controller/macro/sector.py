"""Controllers for sector and industry data endpoints."""

import asyncio
from typing import Dict, Any, Optional

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.macro.sector_service import (
    SectorPerformanceService,
    SectorPEService,
    IndustryPerformanceService,
    IndustryPEService,
)


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
