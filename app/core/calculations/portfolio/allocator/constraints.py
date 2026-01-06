"""
Constraint Builder Module

Builds EfficientFrontier objects with hard/soft constraints for portfolio optimization.
"""

from typing import Dict, List, Tuple

import cvxpy as cp
import pandas as pd
from pypfopt import EfficientFrontier, objective_functions

from app.core.calculations.portfolio.allocator.models import (
    OptimizerConfig,
    ClassifiedTickers,
    validate_weights,
)


def _calc_bucket_bounds(target: float, band: float) -> Tuple[float, float]:
    """Calculate bucket min/max bounds clamped to [0, 1]."""
    return max(0, target - band), min(1, target + band)


class ConstraintBuilder:
    """
    Builds EfficientFrontier with hybrid hard/soft constraints.

    Hard constraints:
    - min_weight floor (every position gets at least X%)
    - hard_max ceiling (no position exceeds Y%)

    Soft constraints (via penalties):
    - Bucket bands (equity/bond/commodity allocation targets)
    - L2 regularization (diversification pressure)
    - Concentration penalty (soft max threshold)
    """

    def __init__(
        self,
        config: OptimizerConfig,
        classified: ClassifiedTickers,
    ):
        self.config = config
        self.classified = classified

        # Position bounds (hard constraints)
        self.min_w = float(config.min_weight)
        self.hard_max_w = float(config.hard_max_weight)
        self.soft_max_w = float(config.soft_max_weight)

        # Bucket bands (clamped to valid range [0, 1])
        self.equity_min, self.equity_max = _calc_bucket_bounds(config.equity_weight_target, config.bucket_band)
        self.bond_min, self.bond_max = _calc_bucket_bounds(config.bond_weight_target, config.bucket_band)
        self.commodity_min, self.commodity_max = _calc_bucket_bounds(config.commodity_weight_target, config.bucket_band)

    def build_ef(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
    ) -> EfficientFrontier:
        """
        Build EfficientFrontier with all constraints applied.

        Args:
            mu: Expected returns series
            S: Covariance matrix DataFrame
            tickers: Ordered list of ticker symbols

        Returns:
            Configured EfficientFrontier object
        """
        eq_idx = [tickers.index(t) for t in tickers if t in self.classified.equities]
        bnd_idx = [tickers.index(t) for t in tickers if t in self.classified.bonds]
        cmd_idx = [tickers.index(t) for t in tickers if t in self.classified.commodities]

        # Hard bounds: min_weight floor, hard_max ceiling
        ef = EfficientFrontier(mu, S, weight_bounds=(self.min_w, self.hard_max_w))

        # Bucket band constraints (only for non-empty buckets with non-zero targets)
        self._add_bucket_constraints(ef, eq_idx, bnd_idx, cmd_idx)

        # Regularization penalties
        self._add_regularization(ef)

        # Concentration penalty
        self._add_concentration_penalty(ef)

        return ef

    def _add_bucket_constraints(
        self,
        ef: EfficientFrontier,
        eq_idx: List[int],
        bnd_idx: List[int],
        cmd_idx: List[int],
    ) -> None:
        """Add bucket band constraints for equity, bond, and commodity allocations."""
        if eq_idx and self.config.equity_weight_target > 0:
            ef.add_constraint(lambda w, eq=eq_idx: w[eq].sum() >= self.equity_min)
            ef.add_constraint(lambda w, eq=eq_idx: w[eq].sum() <= self.equity_max)

        if bnd_idx and self.config.bond_weight_target > 0:
            ef.add_constraint(lambda w, bnd=bnd_idx: w[bnd].sum() >= self.bond_min)
            ef.add_constraint(lambda w, bnd=bnd_idx: w[bnd].sum() <= self.bond_max)

        if cmd_idx and self.config.commodity_weight_target > 0:
            ef.add_constraint(lambda w, cmd=cmd_idx: w[cmd].sum() >= self.commodity_min)
            ef.add_constraint(lambda w, cmd=cmd_idx: w[cmd].sum() <= self.commodity_max)

    def _add_regularization(self, ef: EfficientFrontier) -> None:
        """Add L2 regularization for diversification pressure."""
        if self.config.l2_gamma > 0:
            ef.add_objective(objective_functions.L2_reg, gamma=self.config.l2_gamma)

    def _add_concentration_penalty(self, ef: EfficientFrontier) -> None:
        """Add penalty for weights exceeding soft_max threshold."""
        if self.config.concentration_gamma > 0:
            soft_max = self.soft_max_w
            gamma = self.config.concentration_gamma

            def concentration_cost(w, sm=soft_max, g=gamma):
                excess = cp.pos(w - sm)  # max(0, w - soft_max)
                return g * cp.sum_squares(excess)

            ef.add_objective(concentration_cost)

    def finalize_weights(
        self,
        ef: EfficientFrontier,
        tickers: List[str],
    ) -> Dict[str, float]:
        """
        Clean and validate weights from optimized EfficientFrontier.

        Args:
            ef: Optimized EfficientFrontier object
            tickers: List of ticker symbols

        Returns:
            Dict mapping tickers to cleaned weights
        """
        w = ef.clean_weights()
        validate_weights(w, tickers, min_w=self.min_w, hard_max_w=self.hard_max_w)
        return w

    def bucket_weights(self, weights: Dict[str, float]) -> Tuple[float, float, float]:
        """
        Calculate total weights for equity, bond, and commodity buckets.

        Args:
            weights: Dict mapping tickers to weights

        Returns:
            Tuple of (equity_weight, bond_weight, commodity_weight)
        """
        eq_w = sum(weights.get(t, 0) for t in self.classified.equities)
        bnd_w = sum(weights.get(t, 0) for t in self.classified.bonds)
        cmd_w = sum(weights.get(t, 0) for t in self.classified.commodities)
        return float(eq_w), float(bnd_w), float(cmd_w)
