"""Backtest results, metric calculators, and alpha-level diagnostics.

``BacktestResult`` is the canonical return type for ``Backtest.run``.
``calculate_metrics`` computes the performance metrics dict (total
return, Sharpe, drawdown, win rate, profit factor, ...) from an equity
curve + trades DataFrame.

``run_alpha_isolation`` runs each alpha alone through a fresh PCM to
attribute per-alpha contribution. ``AlphaIsolationReport`` is its
result type.
"""

from prophitai_algo_trading.analytics.alpha_isolation import (
    AlphaIsolationReport,
    run_alpha_isolation,
)
from prophitai_algo_trading.analytics.metrics import (
    BacktestResult,
    calculate_metrics,
)

__all__ = [
    "AlphaIsolationReport",
    "BacktestResult",
    "calculate_metrics",
    "run_alpha_isolation",
]
