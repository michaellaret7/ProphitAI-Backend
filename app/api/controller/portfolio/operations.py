"""Controllers for portfolio CRUD operations."""

from fastapi import HTTPException
from typing import Dict, Any, List, Optional
import uuid

from app.services.portfolio import PortfolioService
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.repositories.portfolio_data import retrieve_portfolio


def _verify_portfolio_ownership(portfolio_id: str, user_id: str) -> None:
    """Verify that the portfolio belongs to the user."""
    positions = retrieve_portfolio(portfolio_id=uuid.UUID(portfolio_id))
    if not positions:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    # Check ownership - all positions for a portfolio have the same user_id
    portfolio_user_id = str(positions[0].get("user_id"))
    if portfolio_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")


@handle_controller_errors
async def create_portfolio_controller(
    *,
    user_id: str,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Controller to handle portfolio creation with cache invalidation."""
    if not user_id:
        raise ValueError("userId is required")

    service = PortfolioService()
    data = service.create_portfolio(
        user_id=user_id,
        portfolio_name=portfolio_name,
        positions=positions
    )

    # Invalidate user portfolio list cache
    await cache.clear_pattern(f"user:portfolios:{user_id}")

    return ok_envelope(
        message="Portfolio created successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/portfolios",
        counts=data['counts'],
        payload=data['portfolios'],
        status=201,
    )


@handle_controller_errors
async def update_portfolio_controller(
    *,
    user_id: str,
    portfolio_id: str,
    name: Optional[str] = None,
    is_current: Optional[bool] = None,
    positions: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Controller to handle portfolio updates with cache invalidation."""
    if not user_id:
        raise ValueError("userId is required")
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Verify ownership before update
    _verify_portfolio_ownership(portfolio_id, user_id)

    service = PortfolioService()
    data = service.update_portfolio(
        user_id=user_id,
        portfolio_id=portfolio_id,
        name=name,
        is_current=is_current,
        positions=positions,
    )

    # Invalidate portfolio cache
    await cache.clear_pattern(f"portfolio:returns:{portfolio_id}:*")
    await cache.clear_pattern(f"portfolio:metrics:{portfolio_id}:*")
    await cache.clear_pattern(f"portfolio:positions:{portfolio_id}")

    return ok_envelope(
        message="Portfolio updated successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/portfolios/{portfolio_id}",
        counts=data['counts'],
        payload=data['portfolios'],
    )


@handle_controller_errors
async def delete_portfolio_controller(
    *,
    user_id: str,
    portfolio_id: str,
) -> Dict[str, Any]:
    """Controller to handle portfolio deletion with cache invalidation."""
    if not user_id:
        raise ValueError("userId is required")
    if not portfolio_id:
        raise ValueError("portfolioId is required")

    # Verify ownership before delete
    _verify_portfolio_ownership(portfolio_id, user_id)

    service = PortfolioService()
    data = service.delete_portfolio(
        user_id=user_id,
        portfolio_id=portfolio_id
    )

    # Invalidate portfolio cache
    await cache.clear_pattern(f"portfolio:returns:{portfolio_id}:*")
    await cache.clear_pattern(f"portfolio:metrics:{portfolio_id}:*")

    return ok_envelope(
        message="Portfolio deleted successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/portfolios",
        counts=data['counts'],
        payload=data['portfolios'],
    )


@handle_controller_errors
async def get_user_portfolio_list_controller(user_id: str) -> Dict[str, Any]:
    """Controller to handle user portfolio list retrieval."""
    if not user_id:
        raise ValueError("userId is required")

    service = PortfolioService()
    data = service.get_user_portfolios(user_id=user_id)

    return ok_envelope(
        message="User portfolio list retrieved successfully",
        kind="users#portfolios",
        resource_id=data['user_data'].get('id'),
        self_link=f"/api/portfolios",
        counts=data['counts'],
        payload=data['portfolios'],
    )


@handle_controller_errors
async def get_portfolio_positions_controller(
    *,
    portfolio_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Controller to handle portfolio positions retrieval with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

    cache_key = f"portfolio:positions:{portfolio_id}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioService()
    positions = service.get_portfolio_positions(portfolio_id=portfolio_id, user_id=user_id)

    response = ok_envelope(
        message="Portfolio positions retrieved successfully",
        kind="portfolio#positions",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/positions",
        payload=positions,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response
