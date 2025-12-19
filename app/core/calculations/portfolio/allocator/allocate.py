# pyportfolioopt_real_data_test.py
"""
Single-file: production-style class + pytest tests + runnable main block.

User-requested structure:
- Class takes ONE list of tickers
- Class has a method to sort tickers into equity vs fixed income
  - The method body is intentionally left empty for you to implement
- 60/40 (or any split) and min/max weight bounds are configurable and enforced
  for EVERY optimization method via a shared _build_ef() path.

Run:
  python pyportfolioopt_real_data_test.py

Tests:
  pytest -q pyportfolioopt_real_data_test.py
"""

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="max_sharpe transforms the optimization problem")

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

import numpy as np
import pandas as pd

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

import cvxpy as cp
from pypfopt import EfficientFrontier, expected_returns, risk_models, objective_functions

from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

from app.core.calculations.portfolio.allocator.utils import OptimizerConfig, assert_weights_ok, calc_num_shares

# ------------------------
# Optimizer class
# ------------------------

class PortfolioAllocator:
    """
    Portfolio optimizer with:
    - One ticker list input
    - Internal classification step: sort into equity vs fixed income (stub for you)
    - Configurable bucket targets (e.g., 60/40)
    - Configurable position constraints (min/max)
    - All objectives share identical constraint plumbing
    """

    def __init__(
        self,
        tickers: List[str],
        config: OptimizerConfig = OptimizerConfig(),
    ):
        self.config = config
        self.all_tickers: List[str] = list(dict.fromkeys(tickers))  # de-dupe, preserve order
        if not self.all_tickers:
            raise ValueError("tickers list is empty.")

        # Classify tickers into equity vs fixed income
        equities, bonds = self.classify_tickers(self.all_tickers)

        # We keep these as sets for membership checks
        self.equities: Set[str] = set(equities)
        self.bonds: Set[str] = set(bonds)

        # sanity: every ticker must be classified into exactly one bucket
        self._validate_classification()

        # Position bounds (hard constraints)
        self.min_w: float = float(self.config.min_weight)
        self.hard_max_w: float = float(self.config.hard_max_weight)
        self.soft_max_w: float = float(self.config.soft_max_weight)

        # Bucket bands (soft constraints via inequalities)
        self.equity_min = self.config.equity_weight_target - self.config.bucket_band
        self.equity_max = self.config.equity_weight_target + self.config.bucket_band
        self.bond_min = self.config.bond_weight_target - self.config.bucket_band
        self.bond_max = self.config.bond_weight_target + self.config.bucket_band

        self._validate_config()

    # ---------- ticker classification ----------

    def classify_tickers(self, tickers: List[str]) -> Tuple[List[str], List[str]]:
        """
        Return (equity_tickers, fixed_income_tickers).
        """
        fixed_income = []
        equities = []

        with MarketSession() as session:
            for ticker in tickers:
                ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker).first()
                if ticker_obj.is_etf and ticker_obj.industry == "fixed_income_etfs":
                    fixed_income.append(ticker_obj.ticker)
                else:
                    equities.append(ticker_obj.ticker)

        return equities, fixed_income

    # ---------- validation ----------

    def _validate_classification(self):
        if not self.equities:
            raise ValueError("No equity tickers classified.")
        if not self.bonds:
            raise ValueError("No fixed income tickers classified.")

        all_set = set(self.all_tickers)
        overlap = self.equities.intersection(self.bonds)
        if overlap:
            raise ValueError(f"Tickers classified into BOTH equity and fixed income: {sorted(overlap)}")

        classified = self.equities.union(self.bonds)
        missing = all_set.difference(classified)
        extra = classified.difference(all_set)

        if missing:
            raise ValueError(f"Tickers NOT classified into any bucket: {sorted(missing)}")
        if extra:
            raise ValueError(f"Classified tickers not in input list (unexpected): {sorted(extra)}")

    def _validate_config(self):
        # Validate bucket targets
        eq_target = self.config.equity_weight_target
        bnd_target = self.config.bond_weight_target

        if not (0 <= eq_target <= 1 and 0 <= bnd_target <= 1):
            raise ValueError("equity_weight_target and bond_weight_target must be within [0,1].")
        if abs((eq_target + bnd_target) - 1.0) > 1e-9:
            raise ValueError("Bucket weight targets must sum to 1.0.")

        # Validate bucket bands
        if self.config.bucket_band < 0:
            raise ValueError("bucket_band must be >= 0.")
        if self.equity_min < 0 or self.bond_min < 0:
            raise ValueError("Bucket bands result in negative minimums.")
        if self.equity_max > 1 or self.bond_max > 1:
            raise ValueError("Bucket bands result in maximums > 1.")

        # Validate position bounds
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

        # Validate penalty coefficients
        if self.config.l2_gamma < 0:
            raise ValueError("l2_gamma must be >= 0.")
        if self.config.concentration_gamma < 0:
            raise ValueError("concentration_gamma must be >= 0.")

        n = len(self.all_tickers)
        if n * self.min_w > 1.0:
            raise ValueError(f"Infeasible: n*min_weight > 1.0 ({n} * {self.min_w})")

        # Basic feasibility check for bucket constraints with hard bounds
        eq_n = len(self.equities)
        bnd_n = len(self.bonds)

        # Check if bucket bands can be satisfied given hard_max constraint
        eq_feasible_max = eq_n * self.hard_max_w
        bnd_feasible_max = bnd_n * self.hard_max_w

        if self.equity_min > eq_feasible_max:
            raise ValueError(
                f"Equity bucket infeasible: min={self.equity_min:.2%} but max achievable is "
                f"{eq_feasible_max:.2%} with {eq_n} assets at hard_max={self.hard_max_w:.2%}."
            )
        if self.bond_min > bnd_feasible_max:
            raise ValueError(
                f"Bond bucket infeasible: min={self.bond_min:.2%} but max achievable is "
                f"{bnd_feasible_max:.2%} with {bnd_n} assets at hard_max={self.hard_max_w:.2%}."
            )

    # ---------- data ----------

    def fetch_prices(self) -> pd.DataFrame:
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
        tickers = list(prices.columns)
        mu = expected_returns.mean_historical_return(prices, frequency=self.config.trading_days)
        S = risk_models.sample_cov(prices, frequency=self.config.trading_days)
        return tickers, mu, S

    # ---------- constraints plumbing (applies to ALL objectives) ----------

    def _build_ef(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str]) -> EfficientFrontier:
        """
        Build EfficientFrontier with hybrid hard/soft constraints:
        - Hard: min_weight floor, hard_max ceiling
        - Soft: bucket bands, L2 regularization, concentration penalty
        """
        eq_idx = [tickers.index(t) for t in tickers if t in self.equities]
        bnd_idx = [tickers.index(t) for t in tickers if t in self.bonds]

        if not eq_idx or not bnd_idx:
            raise ValueError("Equity/bond indices empty. Ensure prices columns include those tickers.")

        # Hard bounds: min_weight floor (1%), hard_max ceiling (15%)
        ef = EfficientFrontier(mu, S, weight_bounds=(self.min_w, self.hard_max_w))

        # Bucket bands (inequalities instead of exact equality)
        ef.add_constraint(lambda w, eq=eq_idx: w[eq].sum() >= self.equity_min)
        ef.add_constraint(lambda w, eq=eq_idx: w[eq].sum() <= self.equity_max)
        ef.add_constraint(lambda w, bnd=bnd_idx: w[bnd].sum() >= self.bond_min)
        ef.add_constraint(lambda w, bnd=bnd_idx: w[bnd].sum() <= self.bond_max)

        # L2 regularization (diversification pressure)
        if self.config.l2_gamma > 0:
            ef.add_objective(objective_functions.L2_reg, gamma=self.config.l2_gamma)

        # Concentration penalty: penalize weights above soft_max threshold
        if self.config.concentration_gamma > 0:
            soft_max = self.soft_max_w
            gamma = self.config.concentration_gamma

            def concentration_cost(w, sm=soft_max, g=gamma):
                excess = cp.pos(w - sm)  # max(0, w - soft_max)
                return g * cp.sum_squares(excess)

            ef.add_objective(concentration_cost)

        return ef

    def _finalize(self, ef: EfficientFrontier, tickers: List[str]) -> Dict[str, float]:
        w = ef.clean_weights()
        assert_weights_ok(w, tickers, min_w=self.min_w, hard_max_w=self.hard_max_w)
        return w

    def bucket_weights(self, weights: Dict[str, float]) -> Tuple[float, float]:
        eq_w = sum(weights[t] for t in self.equities)
        bnd_w = sum(weights[t] for t in self.bonds)
        return float(eq_w), float(bnd_w)

    # ---------- objectives (constraints apply automatically) ----------

    def optimize_min_vol(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str]) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.min_volatility()
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=True)
        return w, perf

    def optimize_max_sharpe(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str]) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(risk_free_rate=self.config.risk_free_rate, verbose=False)
        return w, perf

    def optimize_max_utility(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], risk_aversion: float = 5.0) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.max_quadratic_utility(risk_aversion=risk_aversion)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=True)
        return w, perf

    def optimize_efficient_risk(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], target_volatility: float = 0.12) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.efficient_risk(target_volatility=target_volatility)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=True)
        return w, perf

    def optimize_efficient_return(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], target_return: float = 0.15) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.efficient_return(target_return=target_return)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=True)
        return w, perf


# ------------------------
# Runnable script logic
# ------------------------

def run(
    tickers: List[str],
    equity_weight_target: float = 0.60,
    bond_weight_target: float = 0.40,
    initial_portfolio_value: float = 10_000,
) -> None:

    if not tickers:
        raise ValueError("tickers list is empty.")

    config = OptimizerConfig(
        # Bucket targets with bands
        equity_weight_target=equity_weight_target,
        bond_weight_target=bond_weight_target,
        bucket_band=0.05,   # ±5% flexibility around targets

        # Initial portfolio value
        initial_portfolio_value=initial_portfolio_value,

        # Position constraints (hybrid hard/soft)
        min_weight=0.01,                      # HARD 1% floor
        soft_max_weight=0.08,                 # Soft 8% threshold
        hard_max_weight=0.15,                 # HARD 15% ceiling

        # Regularization penalties
        l2_gamma=0.1,                         # Diversification pressure
        concentration_gamma=0.5,              # Soft max penalty

        # Other params
        risk_free_rate=0.02,
        lookback_days=504,
        frequency="daily",
        trading_days=252,
    )

    opt = PortfolioAllocator(tickers=tickers, config=config)

    prices = opt.fetch_prices()
    ordered_tickers, mu, S = opt.compute_inputs(prices)

    strategies = [
        ("Min Vol", lambda: opt.optimize_min_vol(mu, S, ordered_tickers)),
        ("Max Sharpe", lambda: opt.optimize_max_sharpe(mu, S, ordered_tickers)),
        ("Max Utility", lambda: opt.optimize_max_utility(mu, S, ordered_tickers, risk_aversion=5.0)),
        ("Efficient Risk", lambda: opt.optimize_efficient_risk(mu, S, ordered_tickers, target_volatility=0.12)),
    ]

    # add the calc num shares here run the w returned from the funcs here 

    return strategies

