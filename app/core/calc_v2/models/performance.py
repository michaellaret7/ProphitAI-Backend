"""Pydantic model for performance metric output."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]

class PerformanceMetrics(BaseModel):
    """Container for portfolio performance metrics."""
    # Tier 1: Core Returns
    annualized_return: Float4
    cumulative_total_return: Float4

    # Tier 2: Risk-Adjusted Ratios (None if undefined — e.g. zero volatility)
    sharpe_ratio: Float4 | None = None
    sortino_ratio: Float4 | None = None
    calmar_ratio: Float4 | None = None
    omega_ratio: Float4 | None = None

    # Tier 3: Market-Relative (None if no benchmark provided)
    alpha: Float4 | None = None
    information_ratio: Float4 | None = None
    treynor_ratio: Float4 | None = None

    # Tier 4: Momentum (None if insufficient data for the period)
    momentum_1m: Float4 | None = None
    momentum_3m: Float4 | None = None
    momentum_6m: Float4 | None = None
    momentum_1yr: Float4 | None = None
    momentum_3yr: Float4 | None = None
    momentum_5yr: Float4 | None = None
