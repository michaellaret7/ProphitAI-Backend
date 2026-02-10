from typing import Annotated
from pydantic import AfterValidator, BaseModel

Float4 = Annotated[float, AfterValidator(lambda v: round(v, 4))]

class PerformanceMetrics(BaseModel):
    """Container for portfolio performance metrics."""
    #  Tier 1: Core Returns
    annualized_return: Float4
    cumulative_total_return: Float4
    alpha: Float4

    # Ratios
    sharpe_ratio: Float4
    sortino_ratio: Float4
    calmar_ratio: Float4
    information_ratio: Float4
    treynor_ratio: Float4
    omega_ratio: Float4

    # Momentum Metrics
    momentum_1m: Float4
    momentum_3m: Float4
    momentum_6m: Float4
    momentum_1yr: Float4
    momentum_3yr: Float4
    momentum_5yr: Float4
