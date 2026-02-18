"""Pydantic model for performance metric output."""

from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]

class PerformanceMetrics(BaseModel):
    """Container for portfolio performance metrics."""
    # Tier 1: Core Returns
    annualized_return: Float4
    cumulative_total_return: Float4

    # Tier 2: Risk-Adjusted Ratios
    sharpe_ratio: Float4
    sortino_ratio: Float4
    calmar_ratio: Float4
    omega_ratio: Float4

    # Tier 3: Market-Relative (None if no benchmark provided)
    alpha: Float4 | None = None
    information_ratio: Float4 | None = None
    treynor_ratio: Float4 | None = None

    # Tier 4: Momentum
    momentum_1m: Float4
    momentum_3m: Float4
    momentum_6m: Float4
    momentum_1yr: Float4
    momentum_3yr: Float4
    momentum_5yr: Float4
