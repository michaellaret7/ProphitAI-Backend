"""Orchestrator for computing all performance metrics."""

import pandas as pd

from prophitai_calculations.config import DEFAULT_RF_ANNUAL
from prophitai_calculations.models.performance import PerformanceMetrics
from prophitai_calculations.performance.ratios import (
    calc_calmar_ratio,
    calc_gain_loss_ratio,
    calc_information_ratio,
    calc_omega_ratio,
    calc_profit_factor,
    calc_sharpe_ratio,
    calc_sortino_ratio,
    calc_tail_ratio,
    calc_treynor_ratio,
    calc_win_rate,
)
from prophitai_calculations.performance.returns import (
    calc_alpha,
    calc_annualized_return,
    calc_cumulative_total_return,
    calc_momentum,
)


def calc_all_performance_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> PerformanceMetrics:
    """Calculate all performance metrics for a portfolio."""
    # Returns
    annualized_return = calc_annualized_return(daily_returns)
    cumulative_total_return = calc_cumulative_total_return(daily_returns)

    # Risk-adjusted ratios
    sharpe_ratio = calc_sharpe_ratio(daily_returns, rf_annual)
    sortino_ratio = calc_sortino_ratio(daily_returns, rf_annual)
    calmar_ratio = calc_calmar_ratio(daily_returns, rf_annual)
    omega_ratio = calc_omega_ratio(daily_returns, rf_annual)

    # Return distribution quality
    win_rate = calc_win_rate(daily_returns)
    profit_factor = calc_profit_factor(daily_returns)
    gain_loss_ratio = calc_gain_loss_ratio(daily_returns)
    tail_ratio = calc_tail_ratio(daily_returns)

    # Benchmark-relative (optional)
    alpha = None
    information_ratio = None
    treynor_ratio = None
    if benchmark_returns is not None:
        alpha = calc_alpha(daily_returns, benchmark_returns, rf_annual)
        information_ratio = calc_information_ratio(daily_returns, benchmark_returns)
        treynor_ratio = calc_treynor_ratio(daily_returns, benchmark_returns, rf_annual)

    # Trailing momentum
    momentum_1m = calc_momentum(daily_returns, 1)
    momentum_3m = calc_momentum(daily_returns, 3)
    momentum_6m = calc_momentum(daily_returns, 6)
    momentum_1yr = calc_momentum(daily_returns, 12)
    momentum_3yr = calc_momentum(daily_returns, 36)
    momentum_5yr = calc_momentum(daily_returns, 60)

    return PerformanceMetrics(
        annualized_return=annualized_return,
        cumulative_total_return=cumulative_total_return,
        alpha=alpha,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        information_ratio=information_ratio,
        treynor_ratio=treynor_ratio,
        omega_ratio=omega_ratio,
        win_rate=win_rate,
        profit_factor=profit_factor,
        gain_loss_ratio=gain_loss_ratio,
        tail_ratio=tail_ratio,
        momentum_1m=momentum_1m,
        momentum_3m=momentum_3m,
        momentum_6m=momentum_6m,
        momentum_1yr=momentum_1yr,
        momentum_3yr=momentum_3yr,
        momentum_5yr=momentum_5yr,
    )
