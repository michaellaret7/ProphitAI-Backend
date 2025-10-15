from fastapi import HTTPException
from typing import Dict, Any
from app.services.alts import ProphitAltsServices, AltsConcentrationService, AltsCorrelationService
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

@handle_controller_errors
async def get_fund_sector_concentration_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund sector concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:sectors:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    # Generate cache key
    cache_key = f"alts:fund:sectors:{fund_name}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute sector concentration
    service = AltsConcentrationService(fund_name=fund_name)
    sector_data = service.get_sector_concentration()

    # Build response
    response = ok_envelope(
        message="Fund sector concentration retrieved successfully",
        kind="prophitAlts#sectors",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/sectors",
        payload=sector_data,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_fund_industry_concentration_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund industry concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:industries:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    cache_key = f"alts:fund:industries:{fund_name}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = AltsConcentrationService(fund_name=fund_name)
    industry_data = service.get_industry_concentration()

    response = ok_envelope(
        message="Fund industry concentration retrieved successfully",
        kind="prophitAlts#industries",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/industries",
        payload=industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_fund_sub_industry_concentration_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund sub-industry concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:sub_industries:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    cache_key = f"alts:fund:sub_industries:{fund_name}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = AltsConcentrationService(fund_name=fund_name)
    sub_industry_data = service.get_sub_industry_concentration()

    response = ok_envelope(
        message="Fund sub-industry concentration retrieved successfully",
        kind="prophitAlts#sub_industries",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/sub-industries",
        payload=sub_industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_fund_industry_positions_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund industry concentration with long/short breakdown

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:industries_positions:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    cache_key = f"alts:fund:industries_positions:{fund_name}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = AltsConcentrationService(fund_name=fund_name)
    industry_data = service.get_industry_concentration_with_positions()

    response = ok_envelope(
        message="Fund industry positions retrieved successfully",
        kind="prophitAlts#industries_positions",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/industries/positions",
        payload=industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_fund_sub_industry_positions_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund sub-industry concentration with long/short breakdown

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:sub_industries_positions:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    cache_key = f"alts:fund:sub_industries_positions:{fund_name}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = AltsConcentrationService(fund_name=fund_name)
    sub_industry_data = service.get_sub_industry_concentration_with_positions()

    response = ok_envelope(
        message="Fund sub-industry positions retrieved successfully",
        kind="prophitAlts#sub_industries_positions",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/sub-industries/positions",
        payload=sub_industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_fund_correlation_matrix_controller(
    *,
    fund_name: str,
) -> Dict[str, Any]:
    """
    Controller to handle fund correlation matrix retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: alts:fund:correlation:{fund_name}
    """
    if not fund_name:
        raise ValueError("fund_name is required")

    cache_key = f"alts:fund:correlation:{fund_name}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = AltsCorrelationService(fund_name=fund_name)
    correlation_data = service.get_correlation_matrix()

    response = ok_envelope(
        message="Fund correlation matrix retrieved successfully",
        kind="prophitAlts#correlation",
        resource_id=fund_name,
        self_link=f"/api/alts/fund/{fund_name}/correlation",
        payload=correlation_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response
