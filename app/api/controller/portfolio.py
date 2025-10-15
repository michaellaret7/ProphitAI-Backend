from fastapi import HTTPException
from typing import Dict, Any, List, Optional
from app.services.portfolio import (
    PortfolioService,
    PortfolioReturnsService,
    PortfolioMetricsService,
    PortfolioConcentrationService,
    PortfolioPerformanceComparisonService,
    PortfolioFactorTiltService,
)
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors

@handle_controller_errors
async def create_portfolio_controller(
    *,
    email: str,
    company_name: str,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Controller to handle portfolio creation with cache invalidation
    """
    # Delegate to service
    service = PortfolioService()
    data = service.create_portfolio(
        email=email,
        company_name=company_name,
        portfolio_name=portfolio_name,
        positions=positions
    )

    # Invalidate user portfolio list cache (new portfolio added)
    await cache.clear_pattern(f"user:portfolios:{email}")

    return ok_envelope(
        message="Portfolio created successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/user/portfolios?email={email}",
        counts=data['counts'],
        payload=data['portfolios'],
        status=201,
    )


@handle_controller_errors
async def update_portfolio_controller(
    *,
    email: str,
    portfolio_id: str,
    name: Optional[str] = None,
    is_current: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio updates with cache invalidation
    """
    # Delegate to service
    service = PortfolioService()
    data = service.update_portfolio(
        email=email,
        portfolio_id=portfolio_id,
        name=name,
        is_current=is_current
    )

    # Invalidate portfolio cache - clear all cached data for this portfolio
    await cache.clear_pattern(f"portfolio:returns:{portfolio_id}:*")
    await cache.clear_pattern(f"portfolio:metrics:{portfolio_id}:*")

    return ok_envelope(
        message="Portfolio updated successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/user/portfolios?email={email}",
        counts=data['counts'],
        payload=data['portfolios'],
    )


@handle_controller_errors
async def delete_portfolio_controller(
    *,
    email: str,
    portfolio_id: str,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio deletion with cache invalidation
    """
    # Delegate to service
    service = PortfolioService()
    data = service.delete_portfolio(
        email=email,
        portfolio_id=portfolio_id
    )

    # Invalidate portfolio cache - clear all cached data for this portfolio
    await cache.clear_pattern(f"portfolio:returns:{portfolio_id}:*")
    await cache.clear_pattern(f"portfolio:metrics:{portfolio_id}:*")

    return ok_envelope(
        message="Portfolio deleted successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/user/portfolios?email={email}",
        counts=data['counts'],
        payload=data['portfolios'],
    )

@handle_controller_errors
async def get_portfolio_returns_controller(
    *,
    portfolio_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio returns calculation with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:returns:{portfolio_id}:{years}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Generate cache key
    cache_key = f"portfolio:returns:{portfolio_id}:{years}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute returns
    service = PortfolioReturnsService(
        portfolio_id=portfolio_id,
        years=years
    )
    returns_data = service.get_returns_series()

    # Build response
    response = ok_envelope(
        message="Portfolio returns retrieved successfully",
        kind="portfolio#returns",
        resource_id=portfolio_id,
        self_link=f"/api/portfolio/returns?portfolioId={portfolio_id}",
        payload=returns_data,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
def get_user_portfolio_list_controller(email: str = "michaellaret7@gmail.com") -> Dict[str, Any]:
    """
    Controller to handle user portfolio list retrieval
    """
    if not email:
        raise ValueError("Email is required")

    # Delegate to service
    service = PortfolioService()
    data = service.get_user_portfolios(email=email)

    return ok_envelope(
        message="User portfolio list retrieved successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/user/portfolios?email={email}",
        counts=data['counts'],
        payload=data['portfolios'],
    )

@handle_controller_errors
async def get_portfolio_positions_controller(
    *,
    portfolio_id: str,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio positions retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:positions:{portfolio_id}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Generate cache key
    cache_key = f"portfolio:positions:{portfolio_id}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - retrieve positions
    service = PortfolioService()
    positions = service.get_portfolio_positions(portfolio_id=portfolio_id)

    # Build response
    response = ok_envelope(
        message="Portfolio positions retrieved successfully",
        kind="portfolio#positions",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/positions",
        payload=positions,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_portfolio_metrics_controller(
    *,
    portfolio_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio metrics retrieval for dashboard cards/tooltips with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:metrics:{portfolio_id}:{years}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Generate cache key
    cache_key = f"portfolio:metrics:{portfolio_id}:{years}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute metrics
    service = PortfolioMetricsService(
        portfolio_id=portfolio_id,
        years=years
    )
    metrics_data = service.get_all_metrics()

    # Build response
    response = ok_envelope(
        message="Portfolio metrics retrieved successfully",
        kind="portfolio#metrics",
        resource_id=portfolio_id,
        self_link=f"/api/portfolio/metrics?portfolioId={portfolio_id}",
        payload=metrics_data,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_portfolio_sector_concentration_controller(
    *,
    portfolio_id: str,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio sector concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:sectors:{portfolio_id}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Generate cache key
    cache_key = f"portfolio:sectors:{portfolio_id}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute sector concentration
    service = PortfolioConcentrationService(portfolio_id=portfolio_id)
    sector_data = service.get_sector_concentration()

    # Build response
    response = ok_envelope(
        message="Portfolio sector concentration retrieved successfully",
        kind="portfolio#sectors",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/sectors",
        payload=sector_data,
    )

    # Cache for 1 day (86400 seconds)
    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_portfolio_industry_concentration_controller(
    *,
    portfolio_id: str,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio industry concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:industries:{portfolio_id}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    cache_key = f"portfolio:industries:{portfolio_id}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioConcentrationService(portfolio_id=portfolio_id)
    industry_data = service.get_industry_concentration()

    response = ok_envelope(
        message="Portfolio industry concentration retrieved successfully",
        kind="portfolio#industries",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/industries",
        payload=industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_portfolio_sub_industry_concentration_controller(
    *,
    portfolio_id: str,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio sub-industry concentration retrieval with caching

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:sub_industries:{portfolio_id}
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    cache_key = f"portfolio:sub_industries:{portfolio_id}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioConcentrationService(portfolio_id=portfolio_id)
    sub_industry_data = service.get_sub_industry_concentration()

    response = ok_envelope(
        message="Portfolio sub-industry concentration retrieved successfully",
        kind="portfolio#sub_industries",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/sub-industries",
        payload=sub_industry_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response

@handle_controller_errors
async def get_portfolio_performance_comparison_controller(
    *,
    portfolio_id: str,
    optimized_weights: Dict[str, float],
    years: int = 2,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio performance comparison between current and optimized portfolios.

    This endpoint is designed to be called after portfolio optimization to provide
    comprehensive performance comparison data including returns, drawdowns, and metrics.

    Args:
        portfolio_id: UUID of the current portfolio
        optimized_weights: Dict of ticker -> allocation percentage (e.g., {"AAPL": 10.5, "MSFT": 15.0})
        years: Number of years of historical data (default 2)

    Returns:
        Dict with returns, drawdowns, and metrics comparison
    """
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not optimized_weights:
        raise ValueError("optimizedWeights is required")

    # Initialize service and compute performance data
    service = PortfolioPerformanceComparisonService(
        portfolio_id=portfolio_id,
        optimized_weights=optimized_weights,
        years=years
    )

    # Get complete performance data
    performance_data = service.get_performance_data()

    # Build response
    response = ok_envelope(
        message="Portfolio performance comparison retrieved successfully",
        kind="portfolio#performanceComparison",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/performance-comparison",
        payload=performance_data,
    )

    return response

@handle_controller_errors
async def get_portfolio_factor_tilt_controller(
    *,
    weights: Dict[str, float],
    factor: str,
    years: int = 1,
) -> Dict[str, Any]:
    """
    Controller to handle portfolio factor tilt calculation with caching.

    Calculates portfolio exposure to a specific factor (value, growth, momentum,
    quality, volatility) considering position weights (long/short).

    Cache TTL: 6 hours (21600s)
    Cache key pattern: portfolio:factors:{factor}:{weights_hash}:{years}

    Args:
        weights: Dict of ticker -> allocation percentage (e.g., {"AAPL": 10.5, "MSFT": -5.0})
        factor: Factor type (value, growth, momentum, quality, volatility)
        years: Number of years of historical data (default 1)

    Returns:
        Dict with net/long/short tilts and per-ticker exposures
    """
    if not weights:
        raise ValueError("weights is required")
    if not factor:
        raise ValueError("factor is required")

    # Generate cache key using sorted weights for consistency
    import hashlib
    import json
    weights_str = json.dumps(weights, sort_keys=True)
    weights_hash = hashlib.md5(weights_str.encode()).hexdigest()[:12]
    cache_key = f"portfolio:factors:{factor}:{weights_hash}:{years}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute factor tilt
    service = PortfolioFactorTiltService(
        weights=weights,
        factor=factor,
        years=years
    )
    factor_data = service.calculate()

    # Build response
    response = ok_envelope(
        message=f"Portfolio {factor} factor tilt calculated successfully",
        kind="portfolio#factorTilt",
        resource_id=f"{factor}_{weights_hash}",
        self_link=f"/api/portfolios/factor-tilt?factor={factor}",
        payload=factor_data,
    )

    # Cache for 6 hours (21600 seconds)
    await cache.set(cache_key, response, ttl=21600)

    return response