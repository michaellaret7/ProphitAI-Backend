# Complete API Endpoint Examples

## Example 1: CRUD Endpoint (User-Authenticated)

### Router: `app/api/routes/portfolio_router.py`

```python
from fastapi import APIRouter, Query, Depends, Path, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from app.api.controller.portfolio import (
    get_user_portfolio_list_controller,
    create_portfolio_controller,
    update_portfolio_controller,
    delete_portfolio_controller,
)
from app.api.auth.clerk import get_clerk_user_id
from app.repositories.user_data import get_all_user_data_by_clerk_id

router = APIRouter(tags=["Portfolios"])


async def get_user_id_from_clerk(clerk_id: str = Depends(get_clerk_user_id)) -> str:
    """Get internal database user_id from Clerk ID."""
    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data.get("id")


class PositionModel(BaseModel):
    ticker: str
    allocation: float = Field(..., ge=0.0, le=1.0, description="Allocation as decimal (0.25 = 25%)")


class CreatePortfolioRequest(BaseModel):
    portfolioName: str
    positions: List[PositionModel]
    initialPortfolioValue: Optional[float] = Field(default=None)


class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    nav: Optional[float] = None
    positions: Optional[Dict] = None

    @field_validator('positions')
    @classmethod
    def validate_allocations(cls, v):
        if v is None:
            return v
        for ticker, value in v.items():
            if isinstance(value, dict):
                allocation = value.get('allocation')
                if allocation is not None and (allocation < 0 or allocation > 1):
                    raise ValueError(f"Allocation for {ticker} must be between 0 and 1")
            else:
                if value < 0 or value > 1:
                    raise ValueError(f"Allocation for {ticker} must be between 0 and 1")
        return v


@router.get("/portfolios")
async def get_user_portfolio_list(user_id: str = Depends(get_user_id_from_clerk)):
    """Get all portfolios for the authenticated user."""
    return await get_user_portfolio_list_controller(user_id=user_id)


@router.post("/portfolios", status_code=201)
async def create_portfolio(
    body: CreatePortfolioRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Create a new portfolio for the authenticated user."""
    return await create_portfolio_controller(
        user_id=user_id,
        portfolio_name=body.portfolioName,
        positions=[p.model_dump() for p in body.positions],
        portfolio_value=body.initialPortfolioValue,
    )


@router.patch("/portfolios/{portfolioId}")
async def patch_portfolio(
    body: UpdatePortfolioRequest,
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Update an existing portfolio."""
    return await update_portfolio_controller(
        user_id=user_id,
        portfolio_id=portfolioId,
        name=body.name,
        nav=body.nav,
        positions=body.positions,
    )


@router.delete("/portfolios/{portfolioId}")
async def delete_portfolio(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Delete a portfolio."""
    return await delete_portfolio_controller(
        user_id=user_id,
        portfolio_id=portfolioId,
    )
```

### Controller: `app/api/controller/portfolio/operations.py`

```python
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.portfolio.portfolio import PortfolioService


@handle_controller_errors
async def get_user_portfolio_list_controller(
    *,
    user_id: str,
) -> Dict[str, Any]:
    """
    Get all portfolios for a user.

    Cache TTL: 1 hour (3600s)
    """
    cache_key = f"user:portfolios:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    service = PortfolioService()
    portfolios = service.get_user_portfolios(user_id=user_id)

    response = ok_envelope(
        message="Portfolios retrieved successfully",
        kind="users#portfolios",
        resource_id=user_id,
        self_link="/api/portfolios",
        counts={
            'currentItemCount': len(portfolios),
            'totalItems': len(portfolios),
        },
        payload=portfolios,
    )

    await cache.set(cache_key, response, ttl=3600)
    return response


@handle_controller_errors
async def create_portfolio_controller(
    *,
    user_id: str,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
    portfolio_value: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a new portfolio."""
    service = PortfolioService()
    data = service.create_portfolio(
        user_id=user_id,
        portfolio_name=portfolio_name,
        positions=positions,
        portfolio_value=portfolio_value,
    )

    # Invalidate user's portfolio cache
    await cache.clear_pattern(f"user:portfolios:{user_id}*")

    return ok_envelope(
        message="Portfolio created successfully",
        kind="users#portfolios",
        resource_id=data.get('id'),
        self_link=f"/api/portfolios/{data.get('id')}",
        payload=data,
        status=201,
    )


@handle_controller_errors
async def update_portfolio_controller(
    *,
    user_id: str,
    portfolio_id: str,
    name: Optional[str] = None,
    nav: Optional[float] = None,
    positions: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Update an existing portfolio."""
    # Verify ownership
    service = PortfolioService()
    if not service.user_owns_portfolio(user_id=user_id, portfolio_id=portfolio_id):
        raise HTTPException(status_code=403, detail="Access denied")

    data = service.update_portfolio(
        portfolio_id=portfolio_id,
        name=name,
        nav=nav,
        positions=positions,
    )

    # Invalidate caches
    await cache.clear_pattern(f"user:portfolios:{user_id}*")
    await cache.clear_pattern(f"portfolio:{portfolio_id}:*")

    return ok_envelope(
        message="Portfolio updated successfully",
        kind="users#portfolios",
        resource_id=portfolio_id,
        payload=data,
    )


@handle_controller_errors
async def delete_portfolio_controller(
    *,
    user_id: str,
    portfolio_id: str,
) -> Dict[str, Any]:
    """Delete a portfolio."""
    service = PortfolioService()
    if not service.user_owns_portfolio(user_id=user_id, portfolio_id=portfolio_id):
        raise HTTPException(status_code=403, detail="Access denied")

    service.delete_portfolio(portfolio_id=portfolio_id)

    # Invalidate caches
    await cache.clear_pattern(f"user:portfolios:{user_id}*")
    await cache.clear_pattern(f"portfolio:{portfolio_id}:*")

    return ok_envelope(
        message="Portfolio deleted successfully",
        kind="users#portfolios",
        resource_id=portfolio_id,
        payload={"deleted": True},
    )
```

### Service: `app/services/portfolio/portfolio.py`

```python
from typing import Dict, Any, List, Optional
from app.repositories.portfolio import (
    get_portfolios_by_user_id,
    create_portfolio_db,
    update_portfolio_db,
    delete_portfolio_db,
    get_portfolio_by_id,
)


class PortfolioService:
    """Service for portfolio CRUD operations."""

    def get_user_portfolios(self, *, user_id: str) -> List[Dict[str, Any]]:
        """Get all portfolios for a user."""
        portfolios = get_portfolios_by_user_id(user_id=user_id)
        return [self._format_portfolio(p) for p in portfolios]

    def create_portfolio(
        self,
        *,
        user_id: str,
        portfolio_name: str,
        positions: List[Dict[str, Any]],
        portfolio_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a new portfolio."""
        # Validation
        if not portfolio_name:
            raise ValueError("Portfolio name is required")
        if not positions:
            raise ValueError("At least one position is required")

        # Validate allocations sum
        total_allocation = sum(p.get('allocation', 0) for p in positions)
        if abs(total_allocation - 1.0) > 0.01:
            raise ValueError(f"Allocations must sum to 1.0, got {total_allocation}")

        # Create in database
        portfolio = create_portfolio_db(
            user_id=user_id,
            name=portfolio_name,
            positions=positions,
            nav=portfolio_value,
        )

        return self._format_portfolio(portfolio)

    def update_portfolio(
        self,
        *,
        portfolio_id: str,
        name: Optional[str] = None,
        nav: Optional[float] = None,
        positions: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Update a portfolio."""
        updates = {}
        if name is not None:
            updates['name'] = name
        if nav is not None:
            updates['nav'] = nav
        if positions is not None:
            updates['positions'] = positions

        if not updates:
            raise ValueError("No updates provided")

        portfolio = update_portfolio_db(portfolio_id=portfolio_id, **updates)
        return self._format_portfolio(portfolio)

    def delete_portfolio(self, *, portfolio_id: str) -> None:
        """Delete a portfolio."""
        delete_portfolio_db(portfolio_id=portfolio_id)

    def user_owns_portfolio(self, *, user_id: str, portfolio_id: str) -> bool:
        """Check if user owns the portfolio."""
        portfolio = get_portfolio_by_id(portfolio_id=portfolio_id)
        return portfolio and portfolio.user_id == user_id

    def _format_portfolio(self, portfolio) -> Dict[str, Any]:
        """Format portfolio for API response."""
        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "nav": portfolio.nav,
            "positions": [
                {
                    "ticker": p.ticker,
                    "allocation": float(p.allocation),
                    "numShares": p.num_shares,
                }
                for p in portfolio.items
            ],
        }
```

---

## Example 2: Analytics Endpoint (Public Data)

### Router: `app/api/routes/ticker_router.py`

```python
from fastapi import APIRouter, Query
from app.api.controller.ticker import get_ticker_fundamentals_controller

router = APIRouter(tags=["Ticker Data"])


@router.get("/ticker/{ticker}/fundamentals")
async def get_ticker_fundamentals(
    ticker: str,
    years: int = Query(5, ge=1, le=10, description="Years of historical data"),
):
    """Get fundamental data for a ticker."""
    return await get_ticker_fundamentals_controller(
        ticker=ticker.upper(),
        years=years,
    )
```

### Controller: `app/api/controller/ticker.py`

```python
from typing import Dict, Any
from app.api.response_envelope import ok_envelope
from app.redis.client import cache
from app.utils.decorators.api_decorators import handle_controller_errors
from app.services.fundamentals.ticker_fundamentals import TickerFundamentalsService


@handle_controller_errors
async def get_ticker_fundamentals_controller(
    *,
    ticker: str,
    years: int = 5,
) -> Dict[str, Any]:
    """
    Get fundamental data for a ticker.

    Cache TTL: 1 day (86400s)
    """
    cache_key = f"ticker:fundamentals:{ticker}:{years}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    service = TickerFundamentalsService(ticker=ticker, years=years)
    data = service.get_fundamentals()

    response = ok_envelope(
        message="Fundamentals retrieved successfully",
        kind="ticker#fundamentals",
        resource_id=ticker,
        self_link=f"/api/ticker/{ticker}/fundamentals",
        payload=data,
    )

    await cache.set(cache_key, response, ttl=86400)
    return response
```

---

## Example 3: POST Endpoint with Complex Validation

### Router

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional, Literal

router = APIRouter(tags=["Portfolio Analytics"])


def validate_decimal_weights(weights: Dict[str, float], min_val: float = 0, max_val: float = 1) -> Dict[str, float]:
    """Validate that all weights are in decimal format."""
    for ticker, weight in weights.items():
        if weight < min_val or weight > max_val:
            raise ValueError(
                f"Weight for {ticker} must be between {min_val} and {max_val}. "
                f"Got {weight}. Use 0.25 for 25%, not 25.0"
            )
    return weights


class PortfolioFactorTiltRequest(BaseModel):
    weights: Dict[str, float] = Field(
        ...,
        description="Weights as {ticker: weight} where weight is decimal. Negative for short positions."
    )
    factor: Literal["value", "growth", "momentum", "quality", "volatility"]
    years: Optional[int] = Field(default=1, ge=1, le=10)

    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v):
        return validate_decimal_weights(v, min_val=-1, max_val=1)


@router.post("/portfolios/factor-tilt")
async def get_portfolio_factor_tilt(body: PortfolioFactorTiltRequest):
    """
    Calculate portfolio factor tilt.

    Returns factor exposure analysis for long and short positions.
    """
    return await get_portfolio_factor_tilt_controller(
        weights=body.weights,
        factor=body.factor,
        years=body.years,
    )
```

### Controller

```python
@handle_controller_errors
async def get_portfolio_factor_tilt_controller(
    *,
    weights: Dict[str, float],
    factor: str,
    years: int = 1,
) -> Dict[str, Any]:
    """
    Calculate portfolio factor tilt.

    Cache TTL: 6 hours (21600s)
    """
    # Create cache key from sorted weights for consistency
    weights_key = "_".join(f"{k}:{v}" for k, v in sorted(weights.items()))
    cache_key = f"portfolio:factor_tilt:{factor}:{years}:{hash(weights_key)}"

    cached = await cache.get(cache_key)
    if cached:
        return cached

    service = PortfolioFactorTiltService(
        weights=weights,
        factor=factor,
        years=years,
    )
    tilt_data = service.calculate_tilt()

    response = ok_envelope(
        message="Factor tilt calculated successfully",
        kind="portfolio#factorTilt",
        payload=tilt_data,
    )

    await cache.set(cache_key, response, ttl=21600)
    return response
```

---

## HTTP Status Codes Reference

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET, PATCH, general success |
| 201 | Created | Successful POST that creates a resource |
| 204 | No Content | Successful DELETE (no response body) |
| 400 | Bad Request | Validation errors (`ValueError` in service) |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but no permission |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Unexpected errors |

---

## Query Parameter Patterns

```python
# Required path parameter
@router.get("/resource/{resourceId}")
async def get_resource(resourceId: str = Path(..., description="Resource ID")):

# Optional query with default
@router.get("/resources")
async def list_resources(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort: str = Query("created", description="Sort field"),
):

# Enum query parameter
from typing import Literal
@router.get("/resources")
async def list_resources(
    status: Literal["active", "inactive", "all"] = Query("all"),
):
```
