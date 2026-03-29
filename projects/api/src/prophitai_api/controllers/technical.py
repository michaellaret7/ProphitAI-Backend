"""Controllers for technical analysis endpoints."""

from typing import Dict, Any, List, Optional

from prophitai_api.utils.response_envelope import ok_envelope
from prophitai_api.cache.redis_client import cache
from prophitai_api.utils.decorators import handle_controller_errors
from prophitai_api.services.technical.technical_service import TechnicalIndicatorService


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
