from fastapi import APIRouter, Query, Depends, Path, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal
from app.api.controller.portfolio import (
    get_user_portfolio_list_controller,
    create_portfolio_controller,
    update_portfolio_controller,
    delete_portfolio_controller,
    get_portfolio_returns_controller,
    get_portfolio_metrics_controller,
    get_portfolio_positions_controller,
    get_portfolio_sector_concentration_controller,
    get_portfolio_industry_concentration_controller,
    get_portfolio_sub_industry_concentration_controller,
    get_portfolio_performance_comparison_controller,
    get_portfolio_factor_tilt_controller,
    get_portfolio_stress_returns_controller,
    rebalance_portfolio_controller,
)
from app.api.auth.clerk import get_clerk_user_id
from app.repositories.user_data import get_all_user_data_by_clerk_id

router = APIRouter(tags=["Portfolios 💼"])


def validate_decimal_weights(weights: Dict[str, float], min_val: float = 0, max_val: float = 1) -> Dict[str, float]:
    """
    Validate that all weights are in decimal format within the specified range.

    Args:
        weights: Dict mapping ticker to weight in decimal format
        min_val: Minimum allowed weight (default 0)
        max_val: Maximum allowed weight (default 1)

    Returns:
        The validated weights dict

    Raises:
        ValueError: If any weight is outside the allowed range
    """
    for ticker, weight in weights.items():
        if weight < min_val or weight > max_val:
            raise ValueError(
                f"Weight for {ticker} must be between {min_val} and {max_val} (decimal format). "
                f"Got {weight}. Use 0.25 for 25%, not 25.0"
            )
    return weights


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


class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    isCurrent: Optional[bool] = None
    positions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Positions as {ticker: allocation} where allocation is decimal (0.25 = 25%). Replaces all positions."
    )

    @field_validator('positions')
    @classmethod
    def validate_allocations(cls, v):
        if v is None:
            return v
        return validate_decimal_weights(v)


class PortfolioPerformanceComparisonRequest(BaseModel):
    portfolioId: str
    optimizedWeights: Dict[str, float] = Field(..., description="Weights as {ticker: weight} where weight is decimal (0.25 = 25%)")
    years: Optional[int] = 2

    @field_validator('optimizedWeights')
    @classmethod
    def validate_weights(cls, v):
        return validate_decimal_weights(v)


class PortfolioFactorTiltRequest(BaseModel):
    weights: Dict[str, float] = Field(..., description="Weights as {ticker: weight} where weight is decimal (0.25 = 25%). Negative for short positions.")
    factor: str
    years: Optional[int] = 1

    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v):
        return validate_decimal_weights(v, min_val=-1, max_val=1)


class PortfolioStressReturnsRequest(BaseModel):
    weights: Dict[str, float] = Field(..., description="Weights as {ticker: weight} where weight is decimal (0.25 = 25%)")
    start_date: str
    end_date: str
    frequency: Optional[str] = 'daily'

    @field_validator('weights')
    @classmethod
    def validate_weights(cls, v):
        return validate_decimal_weights(v)


class RebalancePortfolioRequest(BaseModel):
    portfolioId: Optional[str] = None
    tickers: Optional[List[str]] = None
    equityWeightTarget: Optional[float] = 0.60
    bondWeightTarget: Optional[float] = 0.40
    strategy: Optional[Literal["max_sharpe", "min_vol", "max_utility", "efficient_risk"]] = "max_sharpe"
    initialPortfolioValue: Optional[float] = 100_000

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
    )

@router.patch("/portfolios/{portfolioId}")
async def patch_portfolio(
    body: UpdatePortfolioRequest,
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Update an existing portfolio.

    Can update name, current status, and/or replace all positions.
    If positions dict is provided, all existing positions are replaced.

    Example request body:
    {
        "name": "New Portfolio Name",
        "isCurrent": true,
        "positions": {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.50}
    }
    """
    return await update_portfolio_controller(
        user_id=user_id,
        portfolio_id=portfolioId,
        name=body.name,
        is_current=body.isCurrent,
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

@router.get("/portfolios/{portfolioId}/returns")
async def get_portfolio_returns(
    portfolioId: str = Path(..., description="Portfolio ID"),
    years: int = Query(2, description="Number of years of historical data", ge=1, le=10),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get portfolio returns time series."""
    return await get_portfolio_returns_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
        years=years,
    )

@router.get("/portfolios/{portfolioId}/metrics")
async def get_portfolio_metrics(
    portfolioId: str = Path(..., description="Portfolio ID"),
    years: int = Query(2, description="Number of years of historical data", ge=1, le=10),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get portfolio metrics for dashboard cards and tooltips."""
    return await get_portfolio_metrics_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
        years=years,
    )

@router.get("/portfolios/{portfolioId}/positions")
async def get_portfolio_positions(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get positions for a specific portfolio."""
    return await get_portfolio_positions_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )

@router.get("/portfolios/{portfolioId}/sectors")
async def get_portfolio_sectors(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get portfolio sector concentration as percentage allocations."""
    return await get_portfolio_sector_concentration_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )


@router.get("/portfolios/{portfolioId}/industries")
async def get_portfolio_industries(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get portfolio industry concentration as percentage allocations."""
    return await get_portfolio_industry_concentration_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )


@router.get("/portfolios/{portfolioId}/sub-industries")
async def get_portfolio_sub_industries(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Get portfolio sub-industry concentration as percentage allocations."""
    return await get_portfolio_sub_industry_concentration_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )

@router.post("/portfolios/performance-comparison")
async def get_portfolio_performance_comparison(
    body: PortfolioPerformanceComparisonRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Compare performance between current and optimized portfolios against SPY benchmark."""
    return await get_portfolio_performance_comparison_controller(
        portfolio_id=body.portfolioId,
        user_id=user_id,
        optimized_weights=body.optimizedWeights,
        years=body.years,
    )

@router.post("/portfolios/factor-tilt")
async def get_portfolio_factor_tilt(body: PortfolioFactorTiltRequest):
    """
    Calculate portfolio factor tilt for a specific factor.

    Analyzes portfolio exposure to a given factor (value, growth, momentum, quality, or volatility)
    considering position weights. Supports both long-only and long/short portfolios.

    Returns:
    - factor: Factor name
    - exposure_col: Name of the exposure column used
    - net_tilt: Net portfolio tilt (weighted average exposure across all positions)
    - long_tilt: Average exposure of long positions only
    - short_tilt: Average exposure of short positions only
    - per_ticker_exposure: Dictionary mapping each ticker to its individual factor exposure

    Cache TTL: 6 hours (21600s)

    Example request body:
    {
        "weights": {"AAPL": 0.105, "MSFT": 0.15, "GOOGL": -0.05},
        "factor": "growth",
        "years": 1
    }
    """
    return await get_portfolio_factor_tilt_controller(
        weights=body.weights,
        factor=body.factor,
        years=body.years,
    )

@router.post("/portfolios/stress-returns")
async def get_portfolio_stress_returns(body: PortfolioStressReturnsRequest):
    """
    Calculate portfolio and SPY returns with metrics at different frequencies.

    Analyzes portfolio performance during a specific time period at daily, hourly, or 15-minute
    intervals. Returns time series of returns for both portfolio and SPY, plus metrics
    (total return, volatility, max drawdown, Sharpe ratio).

    Returns:
    - portfolio_returns: List of daily/hourly/15min returns
    - spy_returns: List of daily/hourly/15min returns
    - portfolio_metrics: total_return, volatility, max_drawdown, sharpe_ratio
    - spy_metrics: total_return, volatility, max_drawdown, sharpe_ratio

    Cache TTL: 1 hour (3600s)

    Example request body:
    {
        "weights": {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.25, "AMZN": 0.25},
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "frequency": "daily"
    }
    """
    return await get_portfolio_stress_returns_controller(
        weights=body.weights,
        start_date=body.start_date,
        end_date=body.end_date,
        frequency=body.frequency,
    )


@router.post("/portfolios/rebalance")
async def rebalance_portfolio(
    body: RebalancePortfolioRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Rebalance a portfolio using optimization strategies.

    Optimizes portfolio allocation using one of four strategies:
    - max_sharpe: Maximize Sharpe ratio (risk-adjusted returns)
    - min_vol: Minimize portfolio volatility
    - max_utility: Maximize quadratic utility (return - risk_aversion * variance)
    - efficient_risk: Target a specific volatility level

    Provide either portfolioId (to rebalance existing portfolio) or tickers list (for adhoc optimization).

    Returns:
    - allocations: List of {ticker, weight, num_shares} for each position
    - performance: {expected_return, volatility, sharpe_ratio}
    - strategy: The optimization strategy used

    Example request body:
    {
        "portfolioId": "uuid-here",
        "equityWeightTarget": 0.60,
        "bondWeightTarget": 0.40,
        "strategy": "max_sharpe",
        "initialPortfolioValue": 100000
    }

    Or with tickers:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL", "AGG", "BND"],
        "equityWeightTarget": 0.60,
        "bondWeightTarget": 0.40,
        "strategy": "min_vol",
        "initialPortfolioValue": 50000
    }
    """
    return await rebalance_portfolio_controller(
        user_id=user_id,
        portfolio_id=body.portfolioId,
        tickers=body.tickers,
        equity_weight_target=body.equityWeightTarget,
        bond_weight_target=body.bondWeightTarget,
        strategy=body.strategy,
        initial_portfolio_value=body.initialPortfolioValue,
    )
