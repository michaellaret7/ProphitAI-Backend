from fastapi import HTTPException
from typing import Dict, Any, List, Optional
from app.services.portfolio import PortfolioService
from app.services.portfolio_returns import PortfolioReturnsService
from app.services.portfolio_metrics import PortfolioMetricsService
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
