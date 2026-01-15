from fastapi import APIRouter, Query, Depends, Path, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from app.core.calculations.portfolio.allocator import StrategyLiteral
from app.api.controller.portfolio import (
    get_user_portfolio_list_controller,
    create_portfolio_controller,
    update_portfolio_controller,
    delete_portfolio_controller,
    get_portfolio_returns_controller,
    get_batch_portfolio_returns_controller,
    get_portfolio_metrics_controller,
    get_portfolio_positions_controller,
    get_portfolio_sector_concentration_controller,
    get_portfolio_industry_concentration_controller,
    get_portfolio_sub_industry_concentration_controller,
    get_portfolio_performance_comparison_controller,
    get_portfolio_factor_tilt_controller,
    get_portfolio_stress_returns_controller,
    rebalance_portfolio_controller,
    get_portfolio_preference_controller,
    create_portfolio_preference_controller,
    update_portfolio_preference_controller,
    delete_portfolio_preference_controller,
    get_portfolio_alert_state_controller,
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
    num_shares: Optional[int] = Field(default=None, description="Number of shares (calculated from nav if not provided)")


class CreatePortfolioRequest(BaseModel):
    portfolioName: str
    positions: List[PositionModel]
    initialPortfolioValue: Optional[float] = Field(
        default=None,
        description="Total portfolio value (NAV). If provided, num_shares will be calculated for each position."
    )


class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = None
    nav: Optional[float] = Field(
        default=None,
        description="New portfolio value (NAV). If provided with positions, num_shares will be recalculated."
    )
    isCurrent: Optional[bool] = None
    positions: Optional[Dict] = Field(
        default=None,
        description="Positions to replace all existing. Supports two formats: "
                    "{ticker: allocation} or {ticker: {allocation: float, num_shares: int}}"
    )

    @field_validator('positions')
    @classmethod
    def validate_allocations(cls, v):
        if v is None:
            return v
        # Handle both simple {ticker: allocation} and extended {ticker: {allocation, num_shares}} formats
        for ticker, value in v.items():
            if isinstance(value, dict):
                allocation = value.get('allocation')
                if allocation is not None and (allocation < 0 or allocation > 1):
                    raise ValueError(
                        f"Allocation for {ticker} must be between 0 and 1 (decimal format). "
                        f"Got {allocation}. Use 0.25 for 25%, not 25.0"
                    )
            else:
                # Simple format: value is allocation directly
                if value < 0 or value > 1:
                    raise ValueError(
                        f"Allocation for {ticker} must be between 0 and 1 (decimal format). "
                        f"Got {value}. Use 0.25 for 25%, not 25.0"
                    )
        return v


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
    commodityWeightTarget: Optional[float] = 0.0
    strategy: Optional[StrategyLiteral] = "max_sharpe"
    initialPortfolioValue: Optional[float] = 100_000


# =============================================================================
# PORTFOLIO PREFERENCES MODELS
# =============================================================================

RISK_TOLERANCE_VALUES = [
    'Capital Preservation', 'Income', 'Balanced/Moderate Growth',
    'Growth', 'Aggressive Growth/Speculation'
]
TIME_HORIZON_VALUES = [
    'Short term (0-2 years)', 'Medium term (3-7 years)', 'Long term (8+ years)'
]
LIQUIDITY_NEEDS_VALUES = ['High', 'Medium', 'Low']
SECTOR_PREFERENCE_VALUES = ['Include', 'Exclude', 'Not Selected']


class PortfolioPreferenceRequest(BaseModel):
    """Request model for creating/updating portfolio preferences."""
    description: Optional[str] = Field(default=None, description="Portfolio description")

    # Risk Profile
    riskTolerance: Optional[str] = Field(
        default=None,
        description="One of: Capital Preservation, Income, Balanced/Moderate Growth, Growth, Aggressive Growth/Speculation"
    )
    investmentTimeHorizon: Optional[str] = Field(
        default=None,
        description="One of: Short term (0-2 years), Medium term (3-7 years), Long term (8+ years)"
    )
    liquidityNeeds: Optional[str] = Field(
        default=None,
        description="One of: High, Medium, Low"
    )

    # Asset Allocations (decimal 0-1)
    equitiesAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fixedIncomeAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    commoditiesAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    currenciesAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cryptocurrenciesAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    alternativesHedgeFundsAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    alternativesPeVcAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    cashAllocation: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Equity Sector Preferences
    equitySectorCommunicationServices: Optional[str] = Field(default=None, description="Include, Exclude, or Not Selected")
    equitySectorConsumerDiscretionary: Optional[str] = Field(default=None)
    equitySectorConsumerStaples: Optional[str] = Field(default=None)
    equitySectorEnergy: Optional[str] = Field(default=None)
    equitySectorFinancials: Optional[str] = Field(default=None)
    equitySectorHealthCare: Optional[str] = Field(default=None)
    equitySectorIndustrials: Optional[str] = Field(default=None)
    equitySectorInformationTechnology: Optional[str] = Field(default=None)
    equitySectorMaterials: Optional[str] = Field(default=None)
    equitySectorRealEstate: Optional[str] = Field(default=None)
    equitySectorUtilities: Optional[str] = Field(default=None)

    # Fixed Income Sector Preferences
    fixedIncomeSectorSovereignTreasuries: Optional[str] = Field(default=None)
    fixedIncomeSectorIgCredit: Optional[str] = Field(default=None)
    fixedIncomeSectorHighYield: Optional[str] = Field(default=None)
    fixedIncomeSectorSecuritizedProducts: Optional[str] = Field(default=None)

    # Ticker Lists
    tickersToInclude: Optional[List[str]] = Field(default=None)
    tickersToExclude: Optional[List[str]] = Field(default=None)

    @field_validator('riskTolerance')
    @classmethod
    def validate_risk_tolerance(cls, v):
        if v is not None and v not in RISK_TOLERANCE_VALUES:
            raise ValueError(f"riskTolerance must be one of: {RISK_TOLERANCE_VALUES}")
        return v

    @field_validator('investmentTimeHorizon')
    @classmethod
    def validate_time_horizon(cls, v):
        if v is not None and v not in TIME_HORIZON_VALUES:
            raise ValueError(f"investmentTimeHorizon must be one of: {TIME_HORIZON_VALUES}")
        return v

    @field_validator('liquidityNeeds')
    @classmethod
    def validate_liquidity_needs(cls, v):
        if v is not None and v not in LIQUIDITY_NEEDS_VALUES:
            raise ValueError(f"liquidityNeeds must be one of: {LIQUIDITY_NEEDS_VALUES}")
        return v

    def to_snake_case_dict(self) -> dict:
        """Convert camelCase fields to snake_case for repository."""
        data = self.model_dump(exclude_none=True)
        mapping = {
            'riskTolerance': 'risk_tolerance',
            'investmentTimeHorizon': 'investment_time_horizon',
            'liquidityNeeds': 'liquidity_needs',
            'equitiesAllocation': 'equities_allocation',
            'fixedIncomeAllocation': 'fixed_income_allocation',
            'commoditiesAllocation': 'commodities_allocation',
            'currenciesAllocation': 'currencies_allocation',
            'cryptocurrenciesAllocation': 'cryptocurrencies_allocation',
            'alternativesHedgeFundsAllocation': 'alternatives_hedge_funds_allocation',
            'alternativesPeVcAllocation': 'alternatives_pe_vc_allocation',
            'cashAllocation': 'cash_allocation',
            'equitySectorCommunicationServices': 'equity_sector_communication_services',
            'equitySectorConsumerDiscretionary': 'equity_sector_consumer_discretionary',
            'equitySectorConsumerStaples': 'equity_sector_consumer_staples',
            'equitySectorEnergy': 'equity_sector_energy',
            'equitySectorFinancials': 'equity_sector_financials',
            'equitySectorHealthCare': 'equity_sector_health_care',
            'equitySectorIndustrials': 'equity_sector_industrials',
            'equitySectorInformationTechnology': 'equity_sector_information_technology',
            'equitySectorMaterials': 'equity_sector_materials',
            'equitySectorRealEstate': 'equity_sector_real_estate',
            'equitySectorUtilities': 'equity_sector_utilities',
            'fixedIncomeSectorSovereignTreasuries': 'fixed_income_sector_sovereign_treasuries',
            'fixedIncomeSectorIgCredit': 'fixed_income_sector_ig_credit',
            'fixedIncomeSectorHighYield': 'fixed_income_sector_high_yield',
            'fixedIncomeSectorSecuritizedProducts': 'fixed_income_sector_securitized_products',
            'tickersToInclude': 'tickers_to_include',
            'tickersToExclude': 'tickers_to_exclude',
        }
        return {mapping.get(k, k): v for k, v in data.items()}


@router.get("/portfolios")
async def get_user_portfolio_list(user_id: str = Depends(get_user_id_from_clerk)):
    """Get all portfolios for the authenticated user."""
    return await get_user_portfolio_list_controller(user_id=user_id)

@router.post("/portfolios", status_code=201)
async def create_portfolio(
    body: CreatePortfolioRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Create a new portfolio for the authenticated user.

    If initialPortfolioValue is provided, num_shares will be calculated for each position
    based on current market prices. Positions can optionally include num_shares directly.

    Example request body:
    {
        "portfolioName": "My Portfolio",
        "positions": [
            {"ticker": "AAPL", "allocation": 0.25},
            {"ticker": "MSFT", "allocation": 0.25, "num_shares": 10.5}
        ],
        "initialPortfolioValue": 100000
    }
    """
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
    """
    Update an existing portfolio.

    Can update name, nav, current status, and/or replace all positions.
    If positions dict is provided, all existing positions are replaced.
    If nav is provided with positions, num_shares will be recalculated.

    Example request body (simple format):
    {
        "name": "New Portfolio Name",
        "nav": 150000,
        "isCurrent": true,
        "positions": {"AAPL": 0.25, "MSFT": 0.25, "GOOGL": 0.50}
    }

    Example request body (extended format with num_shares):
    {
        "nav": 150000,
        "positions": {
            "AAPL": {"allocation": 0.25, "num_shares": 50.5},
            "MSFT": {"allocation": 0.25, "num_shares": 30.2}
        }
    }
    """
    return await update_portfolio_controller(
        user_id=user_id,
        portfolio_id=portfolioId,
        name=body.name,
        nav=body.nav,
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


@router.get("/portfolios/batch-returns")
async def get_batch_portfolio_returns(
    portfolioIds: str = Query(..., description="Comma-separated list of portfolio IDs"),
    years: int = Query(3, description="Number of years of historical data", ge=1, le=10),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Get returns for multiple portfolios in a single request.

    Optimized for dashboard loading - fetches price data once for all unique
    tickers across portfolios instead of making N separate requests.

    Args:
        portfolioIds: Comma-separated list of portfolio UUIDs
        years: Number of years of historical data (default 3)

    Returns:
        Dict mapping portfolio_id to returns time series
    """
    portfolio_ids = [pid.strip() for pid in portfolioIds.split(",") if pid.strip()]
    if not portfolio_ids:
        raise HTTPException(status_code=400, detail="portfolioIds is required")

    return await get_batch_portfolio_returns_controller(
        portfolio_ids=portfolio_ids,
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

    Optimizes portfolio allocation using one of five strategies:
    - max_sharpe: Maximize Sharpe ratio (risk-adjusted returns)
    - min_vol: Minimize portfolio volatility
    - max_utility: Maximize quadratic utility (return - risk_aversion * variance)
    - efficient_risk: Target a specific volatility level
    - efficient_return: Target a specific return level

    Provide either portfolioId (to rebalance existing portfolio) or tickers list (for adhoc optimization).

    Returns:
    - allocations: List of {ticker, weight, num_shares} for each position
    - performance: {expected_return, volatility, sharpe_ratio}
    - strategy: The optimization strategy used

    Example request body:
    {
        "portfolioId": "uuid-here",
        "equityWeightTarget": 0.60,
        "bondWeightTarget": 0.30,
        "commodityWeightTarget": 0.10,
        "strategy": "max_sharpe",
        "initialPortfolioValue": 100000
    }

    Or with tickers:
    {
        "tickers": ["AAPL", "MSFT", "GOOGL", "AGG", "BND"],
        "equityWeightTarget": 0.60,
        "bondWeightTarget": 0.40,
        "commodityWeightTarget": 0.0,
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
        commodity_weight_target=body.commodityWeightTarget,
        strategy=body.strategy,
        initial_portfolio_value=body.initialPortfolioValue,
    )


# =============================================================================
# PORTFOLIO PREFERENCES ENDPOINTS
# =============================================================================

@router.get("/portfolios/{portfolioId}/preferences")
async def get_portfolio_preferences(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Get portfolio preferences and investment guidelines.

    Returns risk profile, asset allocation targets, sector preferences,
    and ticker restrictions for the specified portfolio.
    """
    return await get_portfolio_preference_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )


@router.post("/portfolios/{portfolioId}/preferences", status_code=201)
async def create_portfolio_preferences(
    body: PortfolioPreferenceRequest,
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Create portfolio preferences for a portfolio.

    Sets up investment guidelines including:
    - Risk profile (tolerance, time horizon, liquidity needs)
    - Asset allocation targets (equities, fixed income, alternatives, etc.)
    - Sector preferences (include/exclude for equity and fixed income sectors)
    - Ticker restrictions (tickers to include or exclude)

    Example request body:
    {
        "description": "Growth-oriented portfolio",
        "riskTolerance": "Growth",
        "investmentTimeHorizon": "Long term (8+ years)",
        "liquidityNeeds": "Low",
        "equitiesAllocation": 0.70,
        "fixedIncomeAllocation": 0.20,
        "cashAllocation": 0.10,
        "equitySectorInformationTechnology": "Include",
        "equitySectorEnergy": "Exclude",
        "tickersToExclude": ["XOM", "CVX"]
    }
    """
    return await create_portfolio_preference_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
        preference_data=body.to_snake_case_dict(),
    )


@router.patch("/portfolios/{portfolioId}/preferences")
async def update_portfolio_preferences(
    body: PortfolioPreferenceRequest,
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Update portfolio preferences.

    Only provided fields are updated. Omitted fields remain unchanged.

    Example request body (partial update):
    {
        "riskTolerance": "Balanced/Moderate Growth",
        "equitiesAllocation": 0.60,
        "fixedIncomeAllocation": 0.30
    }
    """
    return await update_portfolio_preference_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
        preference_data=body.to_snake_case_dict(),
    )


@router.delete("/portfolios/{portfolioId}/preferences")
async def delete_portfolio_preferences(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """Delete portfolio preferences."""
    return await delete_portfolio_preference_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )


# =============================================================================
# PORTFOLIO ALERT STATE ENDPOINTS
# =============================================================================

@router.get("/portfolios/{portfolioId}/alert-state")
async def get_portfolio_alert_state(
    portfolioId: str = Path(..., description="Portfolio ID"),
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Get portfolio alert state for risk monitoring.

    Returns the current state of risk detection alerts including:
    - **drift**: Allocation drift from target preferences
    - **drawdown**: Position drawdown alerts
    - **correlation**: Portfolio correlation change alerts

    Each alert type includes:
    - `result`: Full detection result with flagged items
    - `last_checked_at`: When the detection last ran
    - `last_alerted_at`: When an alert was last sent (null if never triggered)

    This data is used by the frontend to display current risk status
    and by the monitoring system for alert deduplication.

    Cache TTL: 5 minutes (300s)
    """
    return await get_portfolio_alert_state_controller(
        portfolio_id=portfolioId,
        user_id=user_id,
    )
