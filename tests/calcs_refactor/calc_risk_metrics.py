"""Risk metrics calculation functions for portfolio analysis."""

from typing import cast

import numpy as np
import pandas as pd

from risk_model import RiskMetrics


# =============================================================================
# TIER 1: Essential Risk Metrics
# =============================================================================

def calc_volatility(daily_returns: pd.Series, annualize: bool = True) -> float:
    """Calculate portfolio volatility. Annualized by default using sqrt(252)."""
    vol = float(daily_returns.std())
    return vol * np.sqrt(252) if annualize else vol


def calc_drawdown_series(daily_returns: pd.Series) -> pd.Series:
    """Calculate the drawdown series (decline from peak) from daily returns."""
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def calc_max_drawdown(daily_returns: pd.Series) -> float:
    """Calculate maximum drawdown (largest peak-to-trough decline)."""
    drawdown = calc_drawdown_series(daily_returns)
    return float(drawdown.min())


def calc_var(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Historical Value at Risk (VaR) at given confidence level."""
    percentile = (1 - confidence) * 100
    return float(np.percentile(daily_returns, percentile))


def calc_cvar(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Conditional VaR (Expected Shortfall) — expected loss beyond VaR."""
    var = calc_var(daily_returns, confidence)
    tail_losses = daily_returns[daily_returns <= var]
    return float(tail_losses.mean()) if len(tail_losses) > 0 else var


# =============================================================================
# TIER 2: Downside-Focused Metrics
# =============================================================================

def calc_downside_deviation(daily_returns: pd.Series, threshold: float = 0.0, annualize: bool = True) -> float:
    """Calculate downside deviation (semi-deviation below threshold)."""
    downside_returns = daily_returns[daily_returns < threshold]
    if len(downside_returns) == 0:
        return 0.0

    downside_dev = float(downside_returns.std())
    return downside_dev * np.sqrt(252) if annualize else downside_dev


def calc_max_drawdown_duration(daily_returns: pd.Series) -> float:
    """Calculate max drawdown duration (longest underwater period in trading days)."""
    nav = (1 + daily_returns).cumprod()
    hwm = nav.cummax()
    underwater = nav < hwm

    if not underwater.any():
        return 0.0

    # Reason: (~underwater).cumsum() creates group IDs that increment at each new peak,
    # so consecutive underwater days share the same group ID.
    groups = (~underwater).cumsum()
    max_duration = groups[underwater].value_counts().max()

    return float(max_duration)


def calc_ulcer_index(daily_returns: pd.Series) -> float:
    """Calculate Ulcer Index — sqrt(mean(drawdown^2)). Measures drawdown depth and duration."""
    drawdown = calc_drawdown_series(daily_returns)
    return float(np.sqrt((drawdown ** 2).mean()))


# =============================================================================
# TIER 3: Distribution Shape (Tail Risk)
# =============================================================================

def calc_skewness(daily_returns: pd.Series) -> float:
    """Calculate skewness of returns distribution."""
    return float(daily_returns.skew())


def calc_kurtosis(daily_returns: pd.Series) -> float:
    """Calculate excess kurtosis of returns distribution (normal dist = 0)."""
    return float(daily_returns.kurtosis())


# =============================================================================
# TIER 4: Market-Relative Metrics
# =============================================================================

def calc_beta(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate portfolio beta relative to benchmark. Beta = Cov(Rp, Rm) / Var(Rm)."""
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    port_series = cast(pd.Series, aligned['portfolio'])
    bench_series = cast(pd.Series, aligned['benchmark'])

    cov = port_series.cov(bench_series)
    var = bench_series.var()

    return float(cov / var) if var != 0 else 0.0


def calc_tracking_error(daily_returns: pd.Series, benchmark_returns: pd.Series, annualize: bool = True) -> float:
    """Calculate tracking error (active risk) relative to benchmark."""
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    excess_returns = aligned['portfolio'] - aligned['benchmark']
    te = float(excess_returns.std())

    return te * np.sqrt(252) if annualize else te


def calc_upside_capture(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate upside capture ratio (% of benchmark gains captured in up markets)."""
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    # Filter for up market days (benchmark > 0)
    up_market = aligned[aligned['benchmark'] > 0]

    if len(up_market) == 0:
        return 0.0

    # Use ratio of mean returns (standard methodology)
    portfolio_avg = float(up_market['portfolio'].mean())
    benchmark_avg = float(up_market['benchmark'].mean())

    if benchmark_avg == 0:
        return 0.0

    return (portfolio_avg / benchmark_avg) * 100


def calc_downside_capture(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Calculate downside capture ratio (% of benchmark losses captured in down markets)."""
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    # Filter for down market days (benchmark < 0)
    down_market = aligned[aligned['benchmark'] < 0]

    if len(down_market) == 0:
        return 0.0

    # Use ratio of mean returns (standard methodology)
    portfolio_avg = float(down_market['portfolio'].mean())
    benchmark_avg = float(down_market['benchmark'].mean())

    if benchmark_avg == 0:
        return 0.0

    return (portfolio_avg / benchmark_avg) * 100


# =============================================================================
# Combined Calculation
# =============================================================================

def calc_all_risk_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None
) -> RiskMetrics:
    """Calculate all risk metrics for a portfolio. Returns a RiskMetrics instance."""
    # Tier 1: Essential
    volatility = calc_volatility(daily_returns)
    max_drawdown = calc_max_drawdown(daily_returns)
    var_95 = calc_var(daily_returns, 0.95)
    var_99 = calc_var(daily_returns, 0.99)
    cvar_95 = calc_cvar(daily_returns, 0.95)
    cvar_99 = calc_cvar(daily_returns, 0.99)

    # Tier 2: Downside-Focused
    downside_deviation = calc_downside_deviation(daily_returns)
    ulcer_index = calc_ulcer_index(daily_returns)
    max_drawdown_duration = calc_max_drawdown_duration(daily_returns)

    # Tier 3: Distribution Shape (Tail Risk)
    skewness = calc_skewness(daily_returns)
    kurtosis = calc_kurtosis(daily_returns)

    # Tier 4: Market-Relative (optional)
    beta = None
    tracking_error = None
    upside_capture = None
    downside_capture = None
    if benchmark_returns is not None:
        beta = calc_beta(daily_returns, benchmark_returns)
        tracking_error = calc_tracking_error(daily_returns, benchmark_returns)
        upside_capture = calc_upside_capture(daily_returns, benchmark_returns)
        downside_capture = calc_downside_capture(daily_returns, benchmark_returns)

    return RiskMetrics(
        volatility=volatility,
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
        tracking_error=tracking_error,
        upside_capture=upside_capture,
        downside_capture=downside_capture,
    )
