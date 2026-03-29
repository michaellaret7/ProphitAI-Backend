"""Pydantic models for factor exposures (ticker-level and portfolio-level)."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]


# ================================
# --> Ticker-Level Factor Models
# ================================

class MomentumFactors(BaseModel):
    """Price-momentum factor exposures (computed from OHLCV)."""
    r12_1: Float4 | None = None
    r6_1: Float4 | None = None
    r3_1: Float4 | None = None
    risk_adj_momentum: Float4 | None = None
    pct_from_52w_high: Float4 | None = None


class ValueFactors(BaseModel):
    """Value factor exposures (requires fundamentals)."""
    earnings_yield: Float4 | None = None
    book_to_price: Float4 | None = None
    fcf_yield: Float4 | None = None
    ebitda_to_ev: Float4 | None = None
    dividend_yield: Float4 | None = None


class QualityFactors(BaseModel):
    """Quality factor exposures (requires fundamentals)."""
    gross_profitability: Float4 | None = None
    roe: Float4 | None = None
    roa: Float4 | None = None
    accrual_ratio: Float4 | None = None
    debt_to_equity: Float4 | None = None
    interest_coverage: Float4 | None = None
    altman_z_score: Float4 | None = None


class GrowthFactors(BaseModel):
    """Growth factor exposures (requires fundamentals)."""
    revenue_growth_yoy: Float4 | None = None
    earnings_growth_yoy: Float4 | None = None
    fcf_growth_yoy: Float4 | None = None
    forward_eps_growth: Float4 | None = None
    sustainable_growth_rate: Float4 | None = None


class VolatilityFactors(BaseModel):
    """Volatility / low-risk factor exposures (computed from OHLCV)."""
    realized_vol_1y: Float4 | None = None
    realized_vol_3m: Float4 | None = None
    beta: Float4 | None = None
    idiosyncratic_vol: Float4 | None = None
    max_drawdown_1y: Float4 | None = None


class SizeFactors(BaseModel):
    """Size factor exposures (requires fundamentals)."""
    market_cap: Float4 | None = None
    log_market_cap: Float4 | None = None


class TickerFactors(BaseModel):
    """Top-level container for all factor categories on a single ticker.

    momentum and volatility are always computed from OHLCV data.
    value, quality, growth, size require fundamentals and are None when unavailable.
    """
    momentum: MomentumFactors
    volatility: VolatilityFactors
    value: ValueFactors | None = None
    quality: QualityFactors | None = None
    growth: GrowthFactors | None = None
    size: SizeFactors | None = None


# ================================
# --> Portfolio-Level Factor Models
# ================================

class FactorExposureDetail(BaseModel):
    """Per-factor-metric weighted exposure (portfolio-weighted z-scores)."""
    # Momentum
    r12_1: Float4 | None = None
    r6_1: Float4 | None = None
    risk_adj_momentum: Float4 | None = None
    # Value
    earnings_yield: Float4 | None = None
    book_to_price: Float4 | None = None
    fcf_yield: Float4 | None = None
    ebitda_to_ev: Float4 | None = None
    # Quality
    gross_profitability: Float4 | None = None
    roe: Float4 | None = None
    accrual_ratio: Float4 | None = None
    altman_z_score: Float4 | None = None
    # Growth
    revenue_growth_yoy: Float4 | None = None
    forward_eps_growth: Float4 | None = None
    # Volatility
    realized_vol_1y: Float4 | None = None
    beta: Float4 | None = None
    # Size
    log_market_cap: Float4 | None = None


class PortfolioFactorExposure(BaseModel):
    """Portfolio-level composite factor exposures.

    Composite scores are the mean of z-scored sub-factors, then portfolio-weighted.
    A composite of +1.0 means the portfolio is 1 std dev above the cross-sectional average.
    """
    momentum: Float4
    value: Float4 | None = None
    quality: Float4 | None = None
    growth: Float4 | None = None
    volatility: Float4
    size: Float4 | None = None

    detail: FactorExposureDetail
