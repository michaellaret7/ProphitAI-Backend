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
PORTFOLIO_CORR_ZSCORE_THRESHOLD = 1.5  # Z-score above this is a significant spike

# Pair-level correlation thresholds
PAIR_CORR_HIGH_THRESHOLD = 0.85  # Individual pair correlation above this is highly correlated
PAIR_CORR_SPIKE_THRESHOLD = 0.40  # Pair correlation increase above this is concerning

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


class PairCorrelationDetails(BaseModel):
    """Details for a single ticker pair correlation."""
    pair: str
    recent: float
    baseline: float
    change: float


class PairCorrelationResult(BaseModel):
    """Result of pair-level correlation analysis."""
    pairs: list[PairCorrelationDetails]
    flagged_pairs: list[PairCorrelationDetails]
    triggered: bool

