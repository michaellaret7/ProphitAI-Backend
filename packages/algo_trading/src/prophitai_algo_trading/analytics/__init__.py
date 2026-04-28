"""Backtest results, metric calculators, and the alpha-research subsystem.

``BacktestResult`` is the canonical return type for ``Backtest.run``.
``calculate_metrics`` computes the performance metrics dict (total
return, Sharpe, drawdown, win rate, profit factor, ...) from an equity
curve + trades DataFrame.

The alpha-research subsystem (``analyze_alpha`` / ``analyze_alphas``)
runs each alpha through the vector engine and produces deep per-alpha
analytics — IC + IC decay, sub-period stability, return correlations,
and (in later PRs) lag sensitivity, cost breakeven, clustering, FDR
correction, and graduation flags.
"""

from prophitai_algo_trading.analytics.alpha_research import (
    STANDARD_CADENCES,
    AlphaReport,
    AnalyticsConfig,
    CrossAlphaReport,
    analyze_alpha,
    analyze_alphas,
    cadence_sweep_for_alpha,
    print_alpha_report,
    print_alpha_research,
)
from prophitai_algo_trading.analytics.metrics import (
    BacktestResult,
    calculate_metrics,
)

__all__ = [
    # Backtest result + metrics
    "BacktestResult",
    "calculate_metrics",
    # Alpha-research subsystem
    "AlphaReport",
    "AnalyticsConfig",
    "CrossAlphaReport",
    "STANDARD_CADENCES",
    "analyze_alpha",
    "analyze_alphas",
    "cadence_sweep_for_alpha",
    "print_alpha_report",
    "print_alpha_research",
]
