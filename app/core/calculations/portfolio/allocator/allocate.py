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

from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

import numpy as np
import pandas as pd

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

from pypfopt import EfficientFrontier, expected_returns, risk_models

from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago


# One list of tickers (example: 9 equities + 6 bond ETFs)
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "JNJ", "V",
    "AGG", "BND", "TLT", "IEF", "LQD", "VCIT"
]


# ------------------------
# Config
# ------------------------

@dataclass(frozen=True)
class OptimizerConfig:
    # Bucket targets (configurable)
    equity_weight: float = 0.60
    bond_weight: float = 0.40

    # Data params
    lookback_days: int = 504
    frequency: str = "daily"
    trading_days: int = 252

    # Solver params
    risk_free_rate: float = 0.02

    # Position constraints (configurable)
    min_weight: float = 0.005                 # strictly positive -> no zeros
    max_weight: Optional[float] = None        # if set, use directly
    max_weight_multiple: float = 1.5          # else max = multiple * (1/n)


def suggested_max_weight(n_assets: int, multiple: float) -> float:
    return float(multiple / n_assets)


def assert_weights_ok(
    cleaned: Dict[str, float],
    tickers: List[str],
    min_w: float,
    max_w: float,
):
    assert set(cleaned.keys()) == set(tickers)
    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    assert np.isfinite(ws).all()
    assert abs(ws.sum() - 1.0) <= 1e-4
    assert (ws >= (min_w - 1e-4)).all(), f"Found weight below min_w={min_w}: {cleaned}"
    assert (ws <= (max_w + 1e-4)).all(), f"Found weight above max_w={max_w}: {cleaned}"


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

        # You will implement this classification logic.
        equities, bonds = self.classify_tickers(self.all_tickers)

        # We keep these as sets for membership checks
        self.equities: Set[str] = set(equities)
        self.bonds: Set[str] = set(bonds)

        # sanity: every ticker must be classified into exactly one bucket
        self._validate_classification()

        # resolve position bounds (configurable)
        self.min_w: float = float(self.config.min_weight)
        if self.config.max_weight is not None:
            self.max_w: float = float(self.config.max_weight)
        else:
            self.max_w = suggested_max_weight(len(self.all_tickers), self.config.max_weight_multiple)

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
        ew = self.config.equity_weight
        bw = self.config.bond_weight

        if not (0 <= ew <= 1 and 0 <= bw <= 1):
            raise ValueError("equity_weight and bond_weight must be within [0,1].")
        if abs((ew + bw) - 1.0) > 1e-9:
            raise ValueError("Bucket weights must sum to 1.0 (equity_weight + bond_weight).")

        if self.min_w < 0:
            raise ValueError("min_weight must be >= 0.")
        if self.max_w <= 0:
            raise ValueError("max_weight must be > 0.")
        if self.min_w >= self.max_w:
            raise ValueError("min_weight must be < max_weight.")

        n = len(self.all_tickers)
        if n * self.min_w > 1.0:
            raise ValueError(f"Infeasible: n*min_weight > 1.0 ({n} * {self.min_w})")

        # Basic feasibility for bucket constraints with min/max:
        eq_n = len(self.equities)
        bnd_n = len(self.bonds)

        def feasible(bucket_target: float, k: int) -> bool:
            lo = k * self.min_w
            hi = k * self.max_w
            return (bucket_target + 1e-9) >= lo and (bucket_target - 1e-9) <= hi

        if not feasible(ew, eq_n):
            raise ValueError(
                f"Equity bucket infeasible: target={ew} but feasible range is "
                f"[{eq_n*self.min_w:.4f}, {eq_n*self.max_w:.4f}] given min/max weights."
            )
        if not feasible(bw, bnd_n):
            raise ValueError(
                f"Bond bucket infeasible: target={bw} but feasible range is "
                f"[{bnd_n*self.min_w:.4f}, {bnd_n*self.max_w:.4f}] given min/max weights."
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
        eq_idx = [tickers.index(t) for t in tickers if t in self.equities]
        bnd_idx = [tickers.index(t) for t in tickers if t in self.bonds]

        if not eq_idx or not bnd_idx:
            raise ValueError("Equity/bond indices empty. Ensure prices columns include those tickers.")

        ef = EfficientFrontier(mu, S, weight_bounds=(self.min_w, self.max_w))

        # bucket constraints (configurable)
        ef.add_constraint(lambda w: w[eq_idx].sum() == self.config.equity_weight)
        ef.add_constraint(lambda w: w[bnd_idx].sum() == self.config.bond_weight)

        return ef

    def _finalize(self, ef: EfficientFrontier, tickers: List[str]) -> Dict[str, float]:
        w = ef.clean_weights()
        assert_weights_ok(w, tickers, min_w=self.min_w, max_w=self.max_w)
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
        perf = ef.portfolio_performance(risk_free_rate=self.config.risk_free_rate, verbose=True)
        return w, perf

    def optimize_max_utility(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], risk_aversion: float = 5.0) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.max_quadratic_utility(risk_aversion=risk_aversion)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=False)
        return w, perf

    def optimize_efficient_risk(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], target_volatility: float = 0.12) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.efficient_risk(target_volatility=target_volatility)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=False)
        return w, perf

    def optimize_efficient_return(self, mu: pd.Series, S: pd.DataFrame, tickers: List[str], target_return: float = 0.15) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        ef = self._build_ef(mu, S, tickers)
        ef.efficient_return(target_return=target_return)
        w = self._finalize(ef, tickers)
        perf = ef.portfolio_performance(verbose=False)
        return w, perf


# ------------------------
# Runnable script logic (classification stub note)
# ------------------------

from typing import Optional, List

def run(
    tickers: Optional[List[str]] = None,
    equity_weight: float = 0.60,
    bond_weight: float = 0.40
) -> None:
    if tickers is None:
        tickers = TICKERS

    config = OptimizerConfig(
        equity_weight=equity_weight,
        bond_weight=bond_weight,
        min_weight=0.005,
        max_weight=None,
        max_weight_multiple=1.5,
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

    for name, fn in strategies:
        w, (ret, vol, sharpe) = fn()
        print(f"\n{name} | ret={ret:.4f} vol={vol:.4f} sharpe={sharpe:.4f}")
        for t, wt in w.items():
            print(f"  {t}: {wt*100:.2f}%")


if __name__ == "__main__":
    run()
