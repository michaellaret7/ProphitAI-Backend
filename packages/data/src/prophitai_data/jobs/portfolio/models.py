"""
Portfolio monitoring data models.

All result models use explicit fields (no computed properties) for clarity
and simplicity. Detection functions compute all values including `triggered`.
"""
from typing import Dict, Literal
from pydantic import BaseModel

# Thresholds for drift detection
DRIFT_THRESHOLD = 0.05  # -> 5%

# Thresholds for drawdown detection
DRAWDOWN_THRESHOLD = -0.10  # -> 10%

# Portfolio-level correlation thresholds
PORTFOLIO_CORR_HIGH_THRESHOLD = 0.50  # Avg pairwise correlation above this is concerning
PORTFOLIO_CORR_SPIKE_THRESHOLD = 0.10  # Avg correlation increase above this is concerning
PORTFOLIO_CORR_ZSCORE_THRESHOLD = 2.0  # Z-score above this is a significant spike
PORTFOLIO_CORR_DISPERSION_THRESHOLD = 0.15  # Dispersion below this indicates high concentration


# Price target change thresholds
PRICE_TARGET_CHANGE_THRESHOLD = 0.05  # -> 5%


class DriftDetails(BaseModel):
    """Details for a single sector that has drifted from target allocation."""
    current_allocation: float
    target_allocation: float
    drift: float


class DriftResult(BaseModel):
    """Result of allocation drift detection."""
    flagged_sectors: Dict[str, DriftDetails]
    triggered: bool


class DrawdownDetails(BaseModel):
    """Details for a single position in drawdown."""
    current_drawdown: float
    max_drawdown: float
    peak_date: str


class DrawdownResult(BaseModel):
    """Result of drawdown detection."""
    flagged_positions: Dict[str, DrawdownDetails]
    triggered: bool


class PortfolioCorrelationResult(BaseModel):
    """
    Result of portfolio-level correlation analysis.

    Attributes:
        recent_avg: Average pairwise correlation over recent period
        baseline_avg: Average pairwise correlation over baseline period
        change: Difference between recent and baseline averages
        dispersion: Standard deviation of recent correlations (low = "one trade" risk)
        z_score: Statistical significance of current correlation spike
        trend: Direction of correlation movement ('Rising', 'Stable', 'Falling')
        triggered: True if correlation spike is significant
    """
    recent_avg: float
    baseline_avg: float
    change: float
    dispersion: float
    z_score: float
    trend: Literal["Rising", "Stable", "Falling", "N/A"]
    triggered: bool

    @classmethod
    def empty(cls) -> "PortfolioCorrelationResult":
        """Return an empty/default result for insufficient data scenarios."""
        return cls(
            recent_avg=0.0,
            baseline_avg=0.0,
            change=0.0,
            dispersion=0.0,
            z_score=0.0,
            trend="N/A",
            triggered=False
        )


class PriceTargetChangeDetails(BaseModel):
    """Details for a single position where price exceeds target."""
    current_price: float
    target_price: float
    deviation: float  # Percentage above target


class PriceTargetChangeResult(BaseModel):
    """Result of price target change detection."""
    flagged_positions: Dict[str, PriceTargetChangeDetails]
    triggered: bool
