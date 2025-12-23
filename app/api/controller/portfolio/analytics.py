"""Controllers for portfolio analytics endpoints."""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any

from app.services.portfolio import (
    PortfolioReturnsService,
    PortfolioMetricsService,
    PortfolioConcentrationService,
    PortfolioPerformanceComparisonService,
    PortfolioFactorTiltService,
)
from app.services.portfolio.stress_returns import StressReturnsService
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from .operations import _verify_portfolio_ownership


@handle_controller_errors
async def get_portfolio_returns_controller(
    *,
    portfolio_id: str,
    user_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """Controller to handle portfolio returns calculation with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

    cache_key = f"portfolio:returns:{portfolio_id}:{years}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioReturnsService(
        portfolio_id=portfolio_id,
        years=years
    )
    returns_data = service.get_returns_series()

    response = ok_envelope(
        message="Portfolio returns retrieved successfully",
        kind="portfolio#returns",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/returns",
        payload=returns_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_portfolio_metrics_controller(
    *,
    portfolio_id: str,
    user_id: str,
    years: int = 2,
) -> Dict[str, Any]:
    """Controller to handle portfolio metrics retrieval with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

    cache_key = f"portfolio:metrics:{portfolio_id}:{years}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioMetricsService(
        portfolio_id=portfolio_id,
        years=years
    )
    metrics_data = service.get_all_metrics()

    response = ok_envelope(
        message="Portfolio metrics retrieved successfully",
        kind="portfolio#metrics",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/metrics",
        payload=metrics_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_portfolio_sector_concentration_controller(
    *,
    portfolio_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Controller to handle portfolio sector concentration retrieval with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

    cache_key = f"portfolio:sectors:{portfolio_id}"

    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    service = PortfolioConcentrationService(portfolio_id=portfolio_id)
    sector_data = service.get_sector_concentration()

    response = ok_envelope(
        message="Portfolio sector concentration retrieved successfully",
        kind="portfolio#sectors",
        resource_id=portfolio_id,
        self_link=f"/api/portfolios/{portfolio_id}/sectors",
        payload=sector_data,
    )

    await cache.set(cache_key, response, ttl=86400)

    return response


@handle_controller_errors
async def get_portfolio_industry_concentration_controller(
    *,
    portfolio_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """Controller to handle portfolio industry concentration retrieval with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

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
    user_id: str,
) -> Dict[str, Any]:
    """Controller to handle portfolio sub-industry concentration retrieval with caching."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

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
    user_id: str,
    optimized_weights: Dict[str, float],
    years: int = 2,
) -> Dict[str, Any]:
    """Controller to handle portfolio performance comparison."""
    if not portfolio_id:
        raise ValueError("portfolioId is required")
    if not user_id:
        raise ValueError("userId is required")
    if not optimized_weights:
        raise ValueError("optimizedWeights is required")

    # Verify ownership
    _verify_portfolio_ownership(portfolio_id, user_id)

    service = PortfolioPerformanceComparisonService(
        portfolio_id=portfolio_id,
        optimized_weights=optimized_weights,
        years=years
    )

    performance_data = service.get_performance_data()

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


@handle_controller_errors
async def get_portfolio_stress_returns_controller(
    *,
    weights: Dict[str, float],
    start_date: str,
    end_date: str,
    frequency: str = 'daily',
) -> Dict[str, Any]:
    """
    Controller to handle portfolio stress returns calculation with caching.

    Calculates portfolio and SPY returns with metrics at different frequencies
    (daily, hourly, 15mins) for a specific time period.

    Cache TTL: 1 hour (3600s)
    Cache key pattern: portfolio:stress:{weights_hash}:{start_date}:{end_date}:{frequency}

    Args:
        weights: Dict of ticker -> allocation percentage (e.g., {"AAPL": 25.0})
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        frequency: Time interval - 'daily', 'hourly', or '15mins'

    Returns:
        Dict with portfolio_returns, spy_returns, portfolio_metrics, spy_metrics
    """
    if not weights:
        raise ValueError("weights is required")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")

    # Generate cache key using sorted weights for consistency
    weights_str = json.dumps(weights, sort_keys=True)
    weights_hash = hashlib.md5(weights_str.encode()).hexdigest()[:12]
    cache_key = f"portfolio:stress:{weights_hash}:{start_date}:{end_date}:{frequency}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)
    if cached_data:
        return cached_data

    # Cache miss - compute stress returns
    service = StressReturnsService(
        weights=weights,
        start_date=datetime.strptime(start_date, '%Y-%m-%d'),
        end_date=datetime.strptime(end_date, '%Y-%m-%d'),
        frequency=frequency
    )
    stress_data = service.get_data()

    # Build response
    response = ok_envelope(
        message=f"Portfolio stress returns calculated successfully",
        kind="portfolio#stressReturns",
        resource_id=f"{weights_hash}_{start_date}_{end_date}",
        self_link=f"/api/portfolios/stress-returns",
        payload=stress_data,
    )

    # Cache for 1 hour (3600 seconds)
    await cache.set(cache_key, response, ttl=3600)

    return response
