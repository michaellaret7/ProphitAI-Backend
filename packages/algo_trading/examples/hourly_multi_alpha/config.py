"""Tunable parameters for the hourly multi-alpha strategy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Config:
    """Single source of truth for every tunable knob.

    Override fields for sweeps or alternate runs:

        cfg = Config(gross_exposure=2.0, universe_size=500)
    """

    # Capital
    initial_capital: float = 1_000_000.0

    # Universe / data window
    universe_size: int = 750
    benchmark_ticker: str = "SPY"
    start: str = "2022-01-01"
    end: str = "2026-01-01"
    frequency: str = "hourly"

    # Portfolio construction
    gross_exposure: float = 1.75
    per_position_cap: float = 0.075
    quantile: float = 0.20
    min_abs_score: float = 0.05
    rebalance_every: timedelta = timedelta(weeks=1)

    # Execution
    cost_per_turnover: float = 0.0001
    min_change_pct: float = 0.005

    # Risk
    intraday_dd_kill: float = 0.03
    portfolio_dd_limit: float = 0.15
    stop_loss_pct: float = 0.05
    trailing_stop_pct: float = 0.08
    max_position_bars: int = 70
    max_position_duration: timedelta = timedelta(days=14)
