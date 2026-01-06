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
    ClassifiedTickers,
)
from app.core.calculations.portfolio.allocator.classifier import (
    classify_tickers,
    auto_adjust_bucket_targets,
)
from app.core.calculations.portfolio.allocator.constraints import ConstraintBuilder
from app.core.calculations.portfolio.allocator.strategies import run_strategy


class PortfolioAllocator:
    """
    Portfolio optimizer with:
    - One ticker list input
    - Internal classification step: sort into equity vs fixed income
    - Configurable bucket targets (e.g., 60/40)
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

        # Classify tickers into equity vs fixed income
        equities, bonds = classify_tickers(self.all_tickers)

        # Build classified tickers object
        self.classified = ClassifiedTickers(
            equities=set(equities),
            bonds=set(bonds),
            all_tickers=self.all_tickers,
        )

        # Auto-adjust bucket targets if only one asset class is present
        self.config = auto_adjust_bucket_targets(config, self.classified)

        # Build constraint handler (needed by validation)
        self.constraint_builder = ConstraintBuilder(self.config, self.classified)

        # Validate classification
        self._validate_classification()

        # Validate configuration
        self._validate_config()

    # Backwards compatibility properties
    @property
    def equities(self) -> Set[str]:
        return self.classified.equities

    @property
    def bonds(self) -> Set[str]:
        return self.classified.bonds

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

    def _validate_classification(self) -> None:
        """Validate that all tickers are properly classified."""
        # Only require equities if equity_weight_target > 0
        if self.config.equity_weight_target > 0 and not self.classified.has_equities:
            raise ValueError("No equity tickers classified but equity_weight_target > 0.")
        # Only require bonds if bond_weight_target > 0
        if self.config.bond_weight_target > 0 and not self.classified.has_bonds:
            raise ValueError("No fixed income tickers classified but bond_weight_target > 0.")

        all_set = set(self.all_tickers)
        overlap = self.classified.equities.intersection(self.classified.bonds)
        if overlap:
            raise ValueError(f"Tickers classified into BOTH equity and fixed income: {sorted(overlap)}")

        classified_set = self.classified.equities.union(self.classified.bonds)
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

        if not (0 <= eq_target <= 1 and 0 <= bnd_target <= 1):
            raise ValueError("equity_weight_target and bond_weight_target must be within [0,1].")
        if abs((eq_target + bnd_target) - 1.0) > 1e-9:
            raise ValueError("Bucket weight targets must sum to 1.0.")

        if self.config.bucket_band < 0:
            raise ValueError("bucket_band must be >= 0.")
        if eq_target > 0 and self.equity_min < 0:
            raise ValueError("Equity bucket band results in negative minimum.")
        if bnd_target > 0 and self.bond_min < 0:
            raise ValueError("Bond bucket band results in negative minimum.")
        if eq_target > 0 and self.equity_max > 1:
            raise ValueError("Equity bucket band results in maximum > 1.")
        if bnd_target > 0 and self.bond_max > 1:
            raise ValueError("Bond bucket band results in maximum > 1.")

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

        # Basic feasibility check for bucket constraints with hard bounds
        eq_n = self.classified.equity_count
        bnd_n = self.classified.bond_count

        if eq_target > 0 and eq_n > 0:
            eq_feasible_max = eq_n * self.hard_max_w
            if self.equity_min > eq_feasible_max:
                raise ValueError(
                    f"Equity bucket infeasible: min={self.equity_min:.2%} but max achievable is "
                    f"{eq_feasible_max:.2%} with {eq_n} assets at hard_max={self.hard_max_w:.2%}."
                )

        if bnd_target > 0 and bnd_n > 0:
            bnd_feasible_max = bnd_n * self.hard_max_w
            if self.bond_min > bnd_feasible_max:
                raise ValueError(
                    f"Bond bucket infeasible: min={self.bond_min:.2%} but max achievable is "
                    f"{bnd_feasible_max:.2%} with {bnd_n} assets at hard_max={self.hard_max_w:.2%}."
                )

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

    def bucket_weights(self, weights: Dict[str, float]) -> Tuple[float, float]:
        """Calculate total weights for equity and bond buckets."""
        return self.constraint_builder.bucket_weights(weights)

    # Optimization methods (delegate to strategies module)

    def optimize_min_vol(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Minimize portfolio volatility."""
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy="min_vol",
            risk_free_rate=self.config.risk_free_rate,
        )

    def optimize_max_sharpe(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Maximize Sharpe ratio."""
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy="max_sharpe",
            risk_free_rate=self.config.risk_free_rate,
        )

    def optimize_max_utility(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
        risk_aversion: float = 5.0,
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Maximize quadratic utility with given risk aversion."""
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy="max_utility",
            risk_free_rate=self.config.risk_free_rate,
            risk_aversion=risk_aversion,
        )

    def optimize_efficient_risk(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
        target_volatility: float = 0.20,
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Maximize return for a given target volatility."""
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy="efficient_risk",
            risk_free_rate=self.config.risk_free_rate,
            target_volatility=target_volatility,
        )

    def optimize_efficient_return(
        self,
        mu: pd.Series,
        S: pd.DataFrame,
        tickers: List[str],
        target_return: float = 0.15,
    ) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """Minimize volatility for a given target return."""
        return run_strategy(
            self.constraint_builder,
            mu, S, tickers,
            strategy="efficient_return",
            risk_free_rate=self.config.risk_free_rate,
            target_return=target_return,
        )
