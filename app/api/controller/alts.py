from fastapi import HTTPException
from typing import Dict, Any
from app.services.alts import ProphitAltsServices
from app.repositories.prophit_alts_data import get_fund_table
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors

@handle_controller_errors
async def get_fund_final_positions_controller(fund_name: str) -> Dict[str, Any]:
    """
    Controller to handle fund final positions retrieval with caching

    Cache TTL: 1 hour (3600s)
    Cache key pattern: alts:fund:{fund_name}
    """
    # Generate cache key
    cache_key = f"alts:fund:{fund_name}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute fund data
    service = ProphitAltsServices(fund_name)
    data = service.get_fund_performance_data()

    # Build response
    response = ok_envelope(
        message="Fund final positions retrieved successfully",
        kind="prophitAlts#fundPerformance",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/data",
        updated=data.get('updated'),
        counts=data['counts'],
        payload=data['payload'],
    )

    # Cache for 1 hour (3600 seconds)
    await cache.set(cache_key, response, ttl=3600)

    return response

@handle_controller_errors
async def get_fund_table_controller() -> Dict[str, Any]:
    """
    Controller to handle fund table retrieval
    """
    table = get_fund_table()
    return ok_envelope(
        message="Fund table retrieved successfully",
        kind="prophitAlts#fundTable",
        resource_id="funds",
        self_link=f"/api/alts/funds",
        payload=table,
    )
