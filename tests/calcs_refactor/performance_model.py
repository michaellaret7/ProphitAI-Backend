from pydantic import BaseModel, Field
from typing import Optional

class PerformanceMetrics(BaseModel):
    """Container for portfolio performance metrics."""
    #  Tier 1: Core Returns
    annualized_return: float
    cumulative_total_return: float
    alpha: float

    # Ratios 
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    treynor_ratio: float
    omega_ratio: float

    # Momentum Metrics
    momentum_1m: float
    momentum_3m: float
    momentum_6m: float
    momentum_1yr: float
    momentum_3yr: float
    momentum_5yr: float

