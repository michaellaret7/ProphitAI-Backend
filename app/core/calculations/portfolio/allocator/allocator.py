"""
Portfolio Allocator Module

Main orchestrator class that combines classification, constraints, and optimization.
"""

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="max_sharpe transforms the optimization problem")

from typing import Dict, List, Set, Tuple

import pandas as pd
from pypfopt import expected_returns, risk_models

from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

from app.core.calculations.portfolio.allocator.models import (
    OptimizerConfig,
    StrategyLiteral,
)
from app.core.calculations.portfolio.allocator.classifier import (
    build_classified_tickers,
    auto_adjust_bucket_targets,
)
from app.core.calculations.portfolio.allocator.constraints import ConstraintBuilder
from app.core.calculations.portfolio.allocator.strategies import run_strategy


def _check_bucket_overlap(
    set_a: Set[str],
    set_b: Set[str],
    name_a: str,
    name_b: str,
) -> None:
    """Check for overlap between two asset class buckets and raise if found."""
    overlap = set_a.intersection(set_b)
    if overlap:
        raise ValueError(f"Tickers classified into BOTH {name_a} and {name_b}: {sorted(overlap)}")


def _check_bucket_feasibility(
    name: str,
    target: float,
    count: int,
    bucket_min: float,
    hard_max: float,
) -> None:
    """Check if a bucket's constraints are feasible."""
    if target > 0 and count > 0:
        feasible_max = count * hard_max
        if bucket_min > feasible_max:
            raise ValueError(
                f"{name} bucket infeasible: min={bucket_min:.2%} but max achievable is "
                f"{feasible_max:.2%} with {count} assets at hard_max={hard_max:.2%}."
            )


class PortfolioAllocator:
    """
    Portfolio optimizer with:
    - One ticker list input
    - Internal classification step: sort into equity, fixed income, and commodities
    - Configurable bucket targets (e.g., 60/30/10)
    - Configurable position constraints (min/max)
    - All objectives share identical constraint plumbing
    """

    def __init__(
        self,
        tickers: List[str],
        config: OptimizerConfig = OptimizerConfig(),
    ):
        self.all_tickers: List[str] = list(dict.fromkeys(tickers))  # de-dupe, preserve order
        if not self.all_tickers:
            raise ValueError("tickers list is empty.")

        # Classify tickers into equity, fixed income, and commodities
        self.classified = build_classified_tickers(self.all_tickers)

        # Auto-adjust bucket targets based on present asset classes
        self.config = auto_adjust_bucket_targets(config, self.classified)

        # Build constraint handler (needed by validation)
        self.constraint_builder = ConstraintBuilder(self.config, self.classified)

        # Validate classification
        self._validate_classification()

        # Validate configuration
        self._validate_config()

    # Property accessors
    @property
    def equities(self) -> Set[str]:
        return self.classified.equities

    @property
    def bonds(self) -> Set[str]:
        return self.classified.bonds

    @property
    def commodities(self) -> Set[str]:
        return self.classified.commodities

    @property
    def min_w(self) -> float:
        return self.constraint_builder.min_w

    @property
    def hard_max_w(self) -> float:
        return self.constraint_builder.hard_max_w

    @property
    def soft_max_w(self) -> float:
        return self.constraint_builder.soft_max_w

    @property
    def equity_min(self) -> float:
        return self.constraint_builder.equity_min

    @property
    def equity_max(self) -> float:
        return self.constraint_builder.equity_max

    @property
    def bond_min(self) -> float:
        return self.constraint_builder.bond_min

    @property
    def bond_max(self) -> float:
        return self.constraint_builder.bond_max

    @property
    def commodity_min(self) -> float:
        return self.constraint_builder.commodity_min

    @property
    def commodity_max(self) -> float:
        return self.constraint_builder.commodity_max

    def _validate_classification(self) -> None:
        """Validate that all tickers are properly classified."""
        # Only require asset class if its weight target > 0
        if self.config.equity_weight_target > 0 and not self.classified.has_equities:
            raise ValueError("No equity tickers classified but equity_weight_target > 0.")
        if self.config.bond_weight_target > 0 and not self.classified.has_bonds:
            raise ValueError("No fixed income tickers classified but bond_weight_target > 0.")
        if self.config.commodity_weight_target > 0 and not self.classified.has_commodities:
            raise ValueError("No commodity tickers classified but commodity_weight_target > 0.")

        # Check for overlaps between all pairs
        bucket_pairs = [
            (self.classified.equities, self.classified.bonds, "equity", "fixed income"),
            (self.classified.equities, self.classified.commodities, "equity", "commodities"),
            (self.classified.bonds, self.classified.commodities, "fixed income", "commodities"),
        ]
        for set_a, set_b, name_a, name_b in bucket_pairs:
            _check_bucket_overlap(set_a, set_b, name_a, name_b)

        # Check for missing/extra classifications
        all_set = set(self.all_tickers)
        classified_set = self.classified.equities.union(self.classified.bonds).union(self.classified.commodities)
        missing = all_set.difference(classified_set)
        extra = classified_set.difference(all_set)

        if missing:
            raise ValueError(f"Tickers NOT classified into any bucket: {sorted(missing)}")
        if extra:
            raise ValueError(f"Classified tickers not in input list (unexpected): {sorted(extra)}")

    def _validate_config(self) -> None:
        """Validate optimizer configuration for feasibility."""
        eq_target = self.config.equity_weight_target
        bnd_target = self.config.bond_weight_target
        cmd_target = self.config.commodity_weight_target

        if not (0 <= eq_target <= 1 and 0 <= bnd_target <= 1 and 0 <= cmd_target <= 1):
            raise ValueError("All weight targets must be within [0,1].")

        if self.config.bucket_band < 0:
            raise ValueError("bucket_band must be >= 0.")
        if eq_target > 0 and self.equity_min < 0:
            raise ValueError("Equity bucket band results in negative minimum.")
        if bnd_target > 0 and self.bond_min < 0:
            raise ValueError("Bond bucket band results in negative minimum.")
        if cmd_target > 0 and self.commodity_min < 0:
            raise ValueError("Commodity bucket band results in negative minimum.")
        if eq_target > 0 and self.equity_max > 1:
            raise ValueError("Equity bucket band results in maximum > 1.")
        if bnd_target > 0 and self.bond_max > 1:
            raise ValueError("Bond bucket band results in maximum > 1.")
        if cmd_target > 0 and self.commodity_max > 1:
            raise ValueError("Commodity bucket band results in maximum > 1.")

        if self.min_w < 0:
            raise ValueError("min_weight must be >= 0.")
        if self.hard_max_w <= 0:
            raise ValueError("hard_max_weight must be > 0.")
        if self.soft_max_w <= 0:
            raise ValueError("soft_max_weight must be > 0.")
        if self.min_w >= self.hard_max_w:
            raise ValueError("min_weight must be < hard_max_weight.")
        if self.soft_max_w > self.hard_max_w:
            raise ValueError("soft_max_weight must be <= hard_max_weight.")

        if self.config.l2_gamma < 0:
            raise ValueError("l2_gamma must be >= 0.")
        if self.config.concentration_gamma < 0:
            raise ValueError("concentration_gamma must be >= 0.")

        n = len(self.all_tickers)
        if n * self.min_w > 1.0:
            raise ValueError(f"Infeasible: n*min_weight > 1.0 ({n} * {self.min_w})")

        # Feasibility check for bucket constraints with hard bounds
        buckets = [
            ("Equity", eq_target, self.classified.equity_count, self.equity_min),
            ("Bond", bnd_target, self.classified.bond_count, self.bond_min),
            ("Commodity", cmd_target, self.classified.commodity_count, self.commodity_min),
        ]
        for name, target, count, bucket_min in buckets:
            _check_bucket_feasibility(name, target, count, bucket_min, self.hard_max_w)

    def fetch_prices(self) -> pd.DataFrame:
        """Fetch historical price data for all tickers."""
        end_date = get_utc_date_str()
        start_date = get_utc_days_ago(self.config.lookback_days).strftime("%Y-%m-%d")

        price_map = fetch_bulk_price_data_for_tickers(
            self.all_tickers,
            start_date,
            end_date,
            frequency=self.config.frequency,
        )

        prices_df = pd.DataFrame(price_map).dropna()
        if prices_df.empty:
            raise ValueError("No price data returned (after dropna). Check tickers/date range.")
        return prices_df

    def compute_inputs(self, prices: pd.DataFrame) -> Tuple[List[str], pd.Series, pd.DataFrame]:
        """Compute expected returns and covariance matrix from price data."""
        tickers = list(prices.columns)
        mu = expected_returns.mean_historical_return(prices, frequency=self.config.trading_days)
        S = risk_models.sample_cov(prices, frequency=self.config.trading_days)
        return tickers, mu, S

    def bucket_weights(self, weights: Dict[str, float]) -> Tuple[float, float, float]:
        """Calculate total weights for equity, bond, and commodity buckets."""
        return self.constraint_builder.bucket_weights(weights)

    def optimize(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
        strategy: StrategyLiteral = "max_sharpe",
        **strategy_params,
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """
        Run optimization with specified strategy.

        Args:
            mu: Expected returns series
            S: Covariance matrix DataFrame
            tickers: Ordered list of ticker symbols
            strategy: Optimization strategy to use
            **strategy_params: Additional parameters for specific strategies:
                - risk_aversion: For max_utility (default: 5.0)
                - target_volatility: For efficient_risk (default: 0.20)
                - target_return: For efficient_return (default: 0.15)

        Returns:
            Tuple of (weights_dict, performance_tuple)
            where performance_tuple is (expected_return, volatility, sharpe_ratio)
        """
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy=strategy,
            risk_free_rate=self.config.risk_free_rate,
            **strategy_params,
        )
