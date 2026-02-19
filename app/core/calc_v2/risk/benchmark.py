"""Benchmark-relative risk metrics — beta, tracking error, capture ratios."""

from typing import cast

import numpy as np
import pandas as pd

from app.core.calc_v2.config import TRADING_DAYS


def align_returns(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    min_obs: int = 2,
) -> pd.DataFrame | None:
    """Align portfolio and benchmark returns by date, dropping NaNs.

    Returns None if fewer than min_obs overlapping observations exist.
    """
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns,
    }).dropna()
    return aligned if len(aligned) >= min_obs else None


def calc_beta(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Calculate portfolio beta relative to benchmark. Beta = Cov(Rp, Rm) / Var(Rm).

    Returns None if insufficient overlapping data or zero benchmark variance.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    port_series = cast(pd.Series, aligned['portfolio'])
    bench_series = cast(pd.Series, aligned['benchmark'])

    cov = port_series.cov(bench_series)
    var = bench_series.var()

    return float(cov / var) if var != 0 else None


def calc_tracking_error(daily_returns: pd.Series, benchmark_returns: pd.Series, annualize: bool = True) -> float | None:
    """Calculate tracking error (active risk) relative to benchmark.

    Returns None if insufficient overlapping data.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    excess_returns = aligned['portfolio'] - aligned['benchmark']
    te = float(excess_returns.std())

    return te * np.sqrt(TRADING_DAYS) if annualize else te


def calc_up_beta(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Calculate up beta — sensitivity to benchmark in up markets (benchmark > 0).

    Returns None if insufficient data or zero benchmark variance in up markets.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    up_market = aligned[aligned['benchmark'] > 0]

    if len(up_market) < 2:
        return None

    port_series = cast(pd.Series, up_market['portfolio'])
    bench_series = cast(pd.Series, up_market['benchmark'])

    var = bench_series.var()
    if var == 0:
        return None

    return float(port_series.cov(bench_series) / var)


def calc_down_beta(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Calculate down beta — sensitivity to benchmark in down markets (benchmark < 0).

    Returns None if insufficient data or zero benchmark variance in down markets.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    down_market = aligned[aligned['benchmark'] < 0]

    if len(down_market) < 2:
        return None

    port_series = cast(pd.Series, down_market['portfolio'])
    bench_series = cast(pd.Series, down_market['benchmark'])

    var = bench_series.var()
    if var == 0:
        return None

    return float(port_series.cov(bench_series) / var)


def calc_upside_capture(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Calculate upside capture ratio (% of benchmark gains captured in up markets).

    Returns None if insufficient data or no up-market days.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    up_market = aligned[aligned['benchmark'] > 0]

    if len(up_market) == 0:
        return None

    portfolio_avg = float(up_market['portfolio'].mean())
    benchmark_avg = float(up_market['benchmark'].mean())

    if benchmark_avg == 0:
        return None

    return (portfolio_avg / benchmark_avg) * 100


def calc_downside_capture(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float | None:
    """Calculate downside capture ratio (% of benchmark losses captured in down markets).

    Returns None if insufficient data or no down-market days.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    down_market = aligned[aligned['benchmark'] < 0]

    if len(down_market) == 0:
        return None

    portfolio_avg = float(down_market['portfolio'].mean())
    benchmark_avg = float(down_market['benchmark'].mean())

    if benchmark_avg == 0:
        return None

    return (portfolio_avg / benchmark_avg) * 100
