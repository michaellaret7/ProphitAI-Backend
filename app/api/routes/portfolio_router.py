from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
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
)

router = APIRouter()

class PositionModel(BaseModel):
    ticker: str
    allocation: float

class CreatePortfolioRequest(BaseModel):
    email: EmailStr
    companyName: str
    portfolioName: str
    positions: List[PositionModel]

class UpdatePortfolioRequest(BaseModel):
    email: EmailStr
    portfolioId: str
    name: Optional[str] = None
    isCurrent: Optional[bool] = None

class DeletePortfolioRequest(BaseModel):
    email: EmailStr
    portfolioId: str

class PortfolioReturnsRequest(BaseModel):
    email: EmailStr
    portfolioId: str

class PortfolioPerformanceComparisonRequest(BaseModel):
    portfolioId: str
    optimizedWeights: Dict[str, float]
    years: Optional[int] = 2

class PortfolioFactorTiltRequest(BaseModel):
    weights: Dict[str, float]
    factor: str
    years: Optional[int] = 1

#TODO: We want to get the portfolios by uuid
@router.get("/portfolios")
def get_user_portfolio_list(email: str = Query("michaellaret7@gmail.com", description="User's email address")):
    """
    Get user portfolio list by email

    Email defaults to hardcoded value until auth is setup.
    """
    return get_user_portfolio_list_controller(email=email)

@router.post("/portfolios", status_code=201)
async def create_portfolio(body: CreatePortfolioRequest):
    return await create_portfolio_controller(
        email=body.email,
        company_name=body.companyName,
        portfolio_name=body.portfolioName,
        positions=[p.dict() for p in body.positions],
    )

@router.patch("/portfolios")
async def patch_portfolio(body: UpdatePortfolioRequest):
    return await update_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
        name=body.name,
        is_current=body.isCurrent,
    )

@router.delete("/portfolios")
async def delete_portfolio(body: DeletePortfolioRequest):
    return await delete_portfolio_controller(
        email=body.email,
        portfolio_id=body.portfolioId,
    )

@router.get("/portfolios/{portfolioId}/returns")
async def get_portfolio_returns(
    portfolioId: str,
    years: int = Query(2, description="Number of years of historical data", ge=1, le=10),
):
    return await get_portfolio_returns_controller(
        portfolio_id=portfolioId,
        years=years,
    )

@router.get("/portfolios/{portfolioId}/metrics")
async def get_portfolio_metrics(
    portfolioId: str,
    years: int = Query(2, description="Number of years of historical data", ge=1, le=10),
):
    """
    Get portfolio metrics for dashboard cards and tooltips.

    Returns risk metrics, asset allocation, and risk exposure.
    """
    return await get_portfolio_metrics_controller(
        portfolio_id=portfolioId,
        years=years,
    )

@router.get("/portfolios/{portfolioId}/positions")
async def get_portfolio_positions(portfolioId: str):
    """
    Get positions for a specific portfolio.

    Returns a list of positions with ticker and allocation for the given portfolio ID.

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:positions:{portfolio_id}
    """
    return await get_portfolio_positions_controller(
        portfolio_id=portfolioId,
    )

@router.get("/portfolios/{portfolioId}/sectors")
async def get_portfolio_sectors(portfolioId: str):
    """
    Get portfolio sector concentration as percentage allocations.

    Returns a dictionary mapping sector names to allocation percentages.

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:sectors:{portfolio_id}
    """
    return await get_portfolio_sector_concentration_controller(
        portfolio_id=portfolioId,
    )

@router.get("/portfolios/{portfolioId}/industries")
async def get_portfolio_industries(portfolioId: str):
    """
    Get portfolio industry concentration as percentage allocations.

    Returns a dictionary mapping industry names to allocation percentages.

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:industries:{portfolio_id}
    """
    return await get_portfolio_industry_concentration_controller(
        portfolio_id=portfolioId,
    )

@router.get("/portfolios/{portfolioId}/sub-industries")
async def get_portfolio_sub_industries(portfolioId: str):
    """
    Get portfolio sub-industry concentration as percentage allocations.

    Cache TTL: 1 day (86400s)
    Cache key pattern: portfolio:sub_industries:{portfolio_id}
    """
    return await get_portfolio_sub_industry_concentration_controller(
        portfolio_id=portfolioId,
    )

@router.post("/portfolios/performance-comparison")
async def get_portfolio_performance_comparison(body: PortfolioPerformanceComparisonRequest):
    """
    Compare performance between current and optimized portfolios against SPY benchmark.

    Returns comprehensive performance data including:
    - Returns time series (indexed to 100)
    - Drawdown time series (underwater chart)
    - Risk & performance metrics (Sharpe, Sortino, volatility, VaR, max drawdown, returns)

    This endpoint is designed to be called after portfolio optimization to provide
    detailed performance comparison data for visualization.
    """
    return await get_portfolio_performance_comparison_controller(
        portfolio_id=body.portfolioId,
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
        "weights": {"AAPL": 10.5, "MSFT": 15.0, "GOOGL": -5.0},
        "factor": "growth",
        "years": 1
    }
    """
    return await get_portfolio_factor_tilt_controller(
        weights=body.weights,
        factor=body.factor,
        years=body.years,
    )
