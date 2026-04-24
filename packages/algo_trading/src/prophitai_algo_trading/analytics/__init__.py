"""Backtest results and metric calculators.

``BacktestResult`` is the canonical return type for ``Backtest.run``.
``calculate_metrics`` is the function every engine calls to compute the
performance metrics dict (total return, Sharpe, drawdown, win rate,
profit factor, etc.) from an equity curve + trades DataFrame.
"""

from prophitai_algo_trading.analytics.metrics import (
    BacktestResult,
    calculate_metrics,
)

__all__ = [
    "BacktestResult",
    "calculate_metrics",
]
