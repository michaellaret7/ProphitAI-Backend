"""Orchestrator for computing all risk metrics."""

import pandas as pd

from app.core.calc_v2.models.risk import RiskMetrics
from app.core.calc_v2.risk.benchmark import (
    calc_beta,
    calc_down_beta,
    calc_downside_capture,
    calc_tracking_error,
    calc_up_beta,
    calc_upside_capture,
)
from app.core.calc_v2.risk.distribution import (
    calc_cvar,
    calc_downside_deviation,
    calc_kurtosis,
    calc_skewness,
    calc_var,
    calc_volatility,
)
from app.core.calc_v2.risk.drawdown import (
    calc_max_drawdown,
    calc_max_drawdown_duration,
    calc_ulcer_index,
)


def calc_all_risk_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
) -> RiskMetrics:
    """Calculate all risk metrics for a portfolio."""
    # Distribution
    volatility = calc_volatility(daily_returns)
    downside_deviation = calc_downside_deviation(daily_returns)
    var_95 = calc_var(daily_returns, 0.95)
    var_99 = calc_var(daily_returns, 0.99)
    cvar_95 = calc_cvar(daily_returns, 0.95)
    cvar_99 = calc_cvar(daily_returns, 0.99)
    skewness = calc_skewness(daily_returns)
    kurtosis = calc_kurtosis(daily_returns)

    # Drawdown
    max_drawdown = calc_max_drawdown(daily_returns)
    max_drawdown_duration = calc_max_drawdown_duration(daily_returns)
    ulcer_index = calc_ulcer_index(daily_returns)

    # Benchmark-relative (optional)
    beta = None
    up_beta = None
    down_beta = None
    tracking_error = None
    upside_capture = None
    downside_capture = None
    if benchmark_returns is not None:
        beta = calc_beta(daily_returns, benchmark_returns)
        tracking_error = calc_tracking_error(daily_returns, benchmark_returns)
        up_beta = calc_up_beta(daily_returns, benchmark_returns)
        down_beta = calc_down_beta(daily_returns, benchmark_returns)
        upside_capture = calc_upside_capture(daily_returns, benchmark_returns)
        downside_capture = calc_downside_capture(daily_returns, benchmark_returns)

    return RiskMetrics(
        annualized_volatility=volatility,
        max_drawdown=max_drawdown,
        var_95=var_95,
        var_99=var_99,
        cvar_95=cvar_95,
        cvar_99=cvar_99,
        downside_deviation=downside_deviation,
        ulcer_index=ulcer_index,
        max_drawdown_duration=max_drawdown_duration,
        skewness=skewness,
        kurtosis=kurtosis,
        beta=beta,
        up_beta=up_beta,
        down_beta=down_beta,
        tracking_error=tracking_error,
        upside_capture=upside_capture,
        downside_capture=downside_capture,
    )
