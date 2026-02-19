"""Portfolio Allocator Models.

All data models, configuration classes, and validation functions for portfolio allocation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Literal, Set

import numpy as np
from pydantic import BaseModel, ConfigDict

from app.core.calc_v2.config import DEFAULT_RF_ANNUAL, TRADING_DAYS


# Tolerance for numerical precision in weight comparisons
WEIGHT_TOLERANCE = 1e-4

# Type alias for strategy parameter - single source of truth
StrategyLiteral = Literal["max_sharpe", "min_vol", "max_utility", "efficient_risk", "efficient_return"]


class OptimizationStrategy(str, Enum):
    """Available optimization strategies."""
    MAX_SHARPE = "max_sharpe"
    MIN_VOL = "min_vol"
    MAX_UTILITY = "max_utility"
    EFFICIENT_RISK = "efficient_risk"
    EFFICIENT_RETURN = "efficient_return"


class OptimizerConfig(BaseModel):
    """Configuration for portfolio optimization."""
    model_config = ConfigDict(frozen=True)

    # Bucket targets with bands (soft constraints)
    # Targets must sum to 1.0 - auto-adjusted if asset classes are missing
    equity_weight_target: float = 0.60
    bond_weight_target: float = 0.40
    commodity_weight_target: float = 0.0
    crypto_weight_target: float = 0.0
    bucket_band: float = 0.05  # ±5% flexibility around targets

    initial_portfolio_value: float = 10_000

    # Data params
    lookback_days: int = 504
    frequency: str = "daily"
    trading_days: int = TRADING_DAYS

    # Solver params
    risk_free_rate: float = DEFAULT_RF_ANNUAL

    # Position constraints (hybrid hard/soft)
    min_weight: float = 0.01  # HARD floor - every ticker gets at least 1%
    soft_max_weight: float = 0.08  # Soft cap - penalty kicks in above 8%
    hard_max_weight: float = 0.15  # HARD ceiling - absolute max 15%

    # Regularization penalties
    l2_gamma: float = 0.1  # L2 regularization for diversification
    concentration_gamma: float = 0.5  # Penalty for exceeding soft_max


class Allocation(BaseModel):
    """Single ticker allocation with weight and share count."""
    ticker: str
    weight: float
    num_shares: int


class PortfolioPerformance(BaseModel):
    """Portfolio performance metrics."""
    expected_return: float
    volatility: float
    sharpe_ratio: float


class AllocationResult(BaseModel):
    """Complete allocation result with allocations and performance."""
    allocations: List[Allocation]
    performance: PortfolioPerformance
    strategy: str


@dataclass
class ClassifiedTickers:
    """Tickers classified into equity, fixed income, commodity, and crypto buckets."""
    equities: Set[str]
    bonds: Set[str]
    commodities: Set[str]
    crypto: Set[str]
    all_tickers: List[str]

    @property
    def has_equities(self) -> bool:
        return len(self.equities) > 0

    @property
    def has_bonds(self) -> bool:
        return len(self.bonds) > 0

    @property
    def has_commodities(self) -> bool:
        return len(self.commodities) > 0

    @property
    def has_crypto(self) -> bool:
        return len(self.crypto) > 0

    @property
    def equity_count(self) -> int:
        return len(self.equities)

    @property
    def bond_count(self) -> int:
        return len(self.bonds)

    @property
    def commodity_count(self) -> int:
        return len(self.commodities)

    @property
    def crypto_count(self) -> int:
        return len(self.crypto)

    @property
    def asset_class_count(self) -> int:
        """Number of asset classes present."""
        return sum([self.has_equities, self.has_bonds, self.has_commodities, self.has_crypto])


def validate_weights(
    cleaned: Dict[str, float],
    tickers: List[str],
    min_w: float,
    hard_max_w: float,
) -> None:
    """Validate portfolio weights against hard bounds.

    Soft constraints are handled via penalties in the objective, not validated here.

    Raises:
        ValueError: If weights violate any hard constraints.
    """
    if set(cleaned.keys()) != set(tickers):
        raise ValueError(
            f"Weight keys {set(cleaned.keys())} do not match tickers {set(tickers)}"
        )

    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    if not np.isfinite(ws).all():
        raise ValueError("Weights contain non-finite values")
    if abs(ws.sum() - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(f"Weights sum to {ws.sum()}, expected 1.0")
    if not (ws >= (min_w - WEIGHT_TOLERANCE)).all():
        raise ValueError(f"Found weight below min_w={min_w}: {cleaned}")
    if not (ws <= (hard_max_w + WEIGHT_TOLERANCE)).all():
        raise ValueError(f"Found weight above hard_max_w={hard_max_w}: {cleaned}")
