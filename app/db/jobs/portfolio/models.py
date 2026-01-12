from typing import Dict
from pydantic import BaseModel, computed_field

DRIFT_THRESHOLD = 0.05  # -> 5%
DRAWDOWN_THRESHOLD = -0.10  # -> 10%

# Portfolio-level correlation thresholds
PORTFOLIO_CORR_HIGH_THRESHOLD = 0.50  # Avg pairwise correlation above this is concerning
PORTFOLIO_CORR_SPIKE_THRESHOLD = 0.10  # Avg correlation increase above this is concerning

# Pair-level correlation thresholds
PAIR_CORR_HIGH_THRESHOLD = 0.85  # Individual pair correlation above this is highly correlated
PAIR_CORR_SPIKE_THRESHOLD = 0.40  # Pair correlation increase above this is concerning

class DriftDetails(BaseModel):
    current_allocation: float
    target_allocation: float
    drift: float

class DriftResult(BaseModel):
    flagged_sectors: Dict[str, DriftDetails]

    @computed_field
    @property
    def triggered(self) -> bool:
        return len(self.flagged_sectors) > 0

    @computed_field
    @property
    def threshold(self) -> float:
        return DRIFT_THRESHOLD

class DrawdownDetails(BaseModel):
    current_drawdown: float
    max_drawdown: float
    peak_date: str

class DrawdownResult(BaseModel):
    flagged_positions: Dict[str, DrawdownDetails]

    @computed_field
    @property
    def triggered(self) -> bool:
        return len(self.flagged_positions) > 0

    @computed_field
    @property
    def threshold(self) -> float:
        return DRAWDOWN_THRESHOLD


class PortfolioCorrelationResult(BaseModel):
    recent: float
    baseline: float
    change: float

    @computed_field
    @property
    def triggered(self) -> bool:
        return (
            self.recent > PORTFOLIO_CORR_HIGH_THRESHOLD
            or self.change > PORTFOLIO_CORR_SPIKE_THRESHOLD
        )

    @computed_field
    @property
    def high_threshold(self) -> float:
        return PORTFOLIO_CORR_HIGH_THRESHOLD

    @computed_field
    @property
    def spike_threshold(self) -> float:
        return PORTFOLIO_CORR_SPIKE_THRESHOLD


class PairCorrelationDetails(BaseModel):
    pair: str
    recent: float
    baseline: float
    change: float


class PairCorrelationResult(BaseModel):
    pairs: list[PairCorrelationDetails]
    flagged_pairs: list[PairCorrelationDetails]

    @computed_field
    @property
    def triggered(self) -> bool:
        return len(self.flagged_pairs) > 0

    @computed_field
    @property
    def high_threshold(self) -> float:
        return PAIR_CORR_HIGH_THRESHOLD

    @computed_field
    @property
    def spike_threshold(self) -> float:
        return PAIR_CORR_SPIKE_THRESHOLD

