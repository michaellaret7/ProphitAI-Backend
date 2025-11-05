"""Controllers for technical analysis endpoints."""

from typing import Dict, Any, List, Optional

from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.technical.technical_service import (
    TechnicalIndicatorService,
    PivotPointService,
)


@handle_controller_errors
async def get_technical_indicators_controller(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    indicators: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get technical indicators for a ticker.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        indicators: List of specific indicators to calculate (optional)

    Returns:
        Response envelope with indicator data
    """
    # Generate cache key
    indicator_str = ",".join(sorted(indicators)) if indicators else "all"
    cache_key = f"technical:indicators:{ticker}:{start_date}:{end_date}:{indicator_str}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute indicators
    service = TechnicalIndicatorService(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        indicators=indicators,
    )
    indicator_data = service.calculate_indicators()

    # Build response envelope
    response = ok_envelope(
        message="Technical indicators retrieved successfully",
        kind="technical#indicators",
        resource_id=ticker,
        self_link=f"/api/technical/indicators?ticker={ticker}&startDate={start_date}&endDate={end_date}",
        payload={
            "ticker": ticker,
            "startDate": start_date,
            "endDate": end_date,
            "indicators": indicator_data,
        },
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_pivot_points_controller(
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    pivot_type: str = "classic",
) -> Dict[str, Any]:
    """
    Get pivot points for a ticker.

    Cache TTL: 1 day (86400s) for historical data

    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        pivot_type: Type of pivot points (classic, fibonacci, camarilla, woodie, demark)

    Returns:
        Response envelope with pivot point data
    """
    # Generate cache key
    cache_key = f"technical:pivots:{ticker}:{start_date}:{end_date}:{pivot_type}"

    # Try cache first
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute pivot points
    service = PivotPointService(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        pivot_type=pivot_type,
    )
    pivot_data = service.calculate_pivot_points()

    # Build response envelope
    response = ok_envelope(
        message=f"{pivot_type.capitalize()} pivot points retrieved successfully",
        kind="technical#pivotPoints",
        resource_id=ticker,
        self_link=f"/api/technical/pivot-points?ticker={ticker}&startDate={start_date}&endDate={end_date}&pivotType={pivot_type}",
        payload={
            "ticker": ticker,
            "startDate": start_date,
            "endDate": end_date,
            "pivotType": pivot_type,
            "pivotPoints": pivot_data,
        },
    )

    # Cache for 1 day
    await cache.set(cache_key, response, ttl=86400)

    return response
