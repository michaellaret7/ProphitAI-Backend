"""Portfolio Allocator Module.

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

from app.core.calc_v2.allocator.models import (
    OptimizerConfig,
    StrategyLiteral,
)
from app.core.calc_v2.allocator.classifier import (
    build_classified_tickers,
    auto_adjust_bucket_targets,
)
from app.core.calc_v2.allocator.constraints import ConstraintBuilder
from app.core.calc_v2.allocator.strategies import run_strategy


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
    """Portfolio optimizer with classification, constraints, and optimization.

    - One ticker list input
    - Internal classification step: sort into equity, fixed income, commodities, and crypto
    - Configurable bucket targets (e.g., 60/20/10/10)
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
    def crypto(self) -> Set[str]:
        return self.classified.crypto

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

    @property
    def crypto_min(self) -> float:
        return self.constraint_builder.crypto_min

    @property
    def crypto_max(self) -> float:
        return self.constraint_builder.crypto_max

    def _validate_classification(self) -> None:
        """Validate that all tickers are properly classified."""
        # Check each bucket has tickers if its target > 0
        bucket_checks = [
            (self.config.equity_weight_target, self.classified.has_equities, "equity"),
            (self.config.bond_weight_target, self.classified.has_bonds, "fixed income"),
            (self.config.commodity_weight_target, self.classified.has_commodities, "commodity"),
            (self.config.crypto_weight_target, self.classified.has_crypto, "crypto"),
        ]
        for target, has_tickers, name in bucket_checks:
            if target > 0 and not has_tickers:
                raise ValueError(f"No {name} tickers classified but {name}_weight_target > 0.")

        # Check for overlaps between all bucket pairs
        all_buckets = [
            (self.classified.equities, "equity"),
            (self.classified.bonds, "fixed income"),
            (self.classified.commodities, "commodities"),
            (self.classified.crypto, "crypto"),
        ]
        for i, (set_a, name_a) in enumerate(all_buckets):
            for set_b, name_b in all_buckets[i + 1:]:
                _check_bucket_overlap(set_a, set_b, name_a, name_b)

        all_set = set(self.all_tickers)
        classified_set = (
            self.classified.equities | self.classified.bonds
            | self.classified.commodities | self.classified.crypto
        )
        missing = all_set.difference(classified_set)
        extra = classified_set.difference(all_set)

        if missing:
            raise ValueError(f"Tickers NOT classified into any bucket: {sorted(missing)}")
        if extra:
            raise ValueError(f"Classified tickers not in input list (unexpected): {sorted(extra)}")

    def _validate_config(self) -> None:
        """Validate optimizer configuration for feasibility."""
        cfg = self.config

        # Scalar rules: (condition_that_must_be_true, error_message)
        rules = [
            (0 <= cfg.equity_weight_target <= 1, "equity_weight_target must be within [0,1]."),
            (0 <= cfg.bond_weight_target <= 1, "bond_weight_target must be within [0,1]."),
            (0 <= cfg.commodity_weight_target <= 1, "commodity_weight_target must be within [0,1]."),
            (0 <= cfg.crypto_weight_target <= 1, "crypto_weight_target must be within [0,1]."),
            (cfg.bucket_band >= 0, "bucket_band must be >= 0."),
            (self.min_w >= 0, "min_weight must be >= 0."),
            (self.hard_max_w > 0, "hard_max_weight must be > 0."),
            (self.soft_max_w > 0, "soft_max_weight must be > 0."),
            (self.min_w < self.hard_max_w, "min_weight must be < hard_max_weight."),
            (self.soft_max_w <= self.hard_max_w, "soft_max_weight must be <= hard_max_weight."),
            (cfg.l2_gamma >= 0, "l2_gamma must be >= 0."),
            (cfg.concentration_gamma >= 0, "concentration_gamma must be >= 0."),
            (len(self.all_tickers) * self.min_w <= 1.0,
             f"Infeasible: n*min_weight > 1.0 ({len(self.all_tickers)} * {self.min_w})"),
        ]
        for condition, msg in rules:
            if not condition:
                raise ValueError(msg)

        # Per-bucket band validation
        buckets = [
            ("Equity", cfg.equity_weight_target, self.equity_min, self.equity_max,
             self.classified.equity_count),
            ("Bond", cfg.bond_weight_target, self.bond_min, self.bond_max,
             self.classified.bond_count),
            ("Commodity", cfg.commodity_weight_target, self.commodity_min, self.commodity_max,
             self.classified.commodity_count),
            ("Crypto", cfg.crypto_weight_target, self.crypto_min, self.crypto_max,
             self.classified.crypto_count),
        ]
        for name, target, bmin, bmax, count in buckets:
            if target > 0:
                if bmin < 0:
                    raise ValueError(f"{name} bucket band results in negative minimum.")
                if bmax > 1:
                    raise ValueError(f"{name} bucket band results in maximum > 1.")
            _check_bucket_feasibility(name, target, count, bmin, self.hard_max_w)

    def fetch_prices(self) -> pd.DataFrame:
        """Fetch historical price data for all tickers."""
        end_date = get_utc_date_str()
        start_date = get_utc_days_ago(self.config.lookback_days).strftime("%Y-%m-%d")

        prices_df = fetch_bulk_price_data_for_tickers(
            self.all_tickers,
            start_date,
            end_date,
            frequency=self.config.frequency,
        ).dropna()
        if prices_df.empty:
            raise ValueError("No price data returned (after dropna). Check tickers/date range.")
        return prices_df

    def compute_inputs(self, prices: pd.DataFrame) -> Tuple[List[str], pd.Series, pd.DataFrame]:
        """Compute expected returns and covariance matrix from price data."""
        tickers = list(prices.columns)
        mu = expected_returns.mean_historical_return(prices, frequency=self.config.trading_days)
        S = risk_models.sample_cov(prices, frequency=self.config.trading_days)
        return tickers, mu, S

    def bucket_weights(self, weights: Dict[str, float]) -> Tuple[float, float, float, float]:
        """Calculate total weights for equity, bond, commodity, and crypto buckets."""
        return self.constraint_builder.bucket_weights(weights)

    def optimize(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
        strategy: StrategyLiteral = "max_sharpe",
        **strategy_params,
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Run optimization with specified strategy.

        Returns:
            Tuple of (weights_dict, performance_tuple)
            where performance_tuple is (expected_return, volatility, sharpe_ratio).
        """
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy=strategy,
            risk_free_rate=self.config.risk_free_rate,
            **strategy_params,
        )


