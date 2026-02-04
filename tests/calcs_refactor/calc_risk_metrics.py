"""
Risk metrics calculation functions for portfolio analysis.

All functions accept a pandas Series of daily returns and return float values.
Metrics are organized into three tiers:
- Tier 1: Essential (volatility, drawdown, VaR, CVaR)
- Tier 2: Downside-focused (downside deviation, ulcer index, avg drawdown)
- Tier 3: Market-relative (beta, tracking error) - requires benchmark
"""

from typing import cast

import numpy as np
import pandas as pd

from risk_model import RiskMetrics


# =============================================================================
# TIER 1: Essential Risk Metrics
# =============================================================================

def calc_volatility(daily_returns: pd.Series, annualize: bool = True) -> float:
    """
    Calculate portfolio volatility (standard deviation of returns).

    Args:
        daily_returns: Series of daily portfolio returns
        annualize: If True, annualize using sqrt(252)

    Returns:
        Volatility as decimal (0.20 = 20%)
    """
    vol = float(daily_returns.std())
    return vol * np.sqrt(252) if annualize else vol


def calc_drawdown_series(daily_returns: pd.Series) -> pd.Series:
    """
    Calculate the drawdown series from daily returns.

    Drawdown measures the decline from a historical peak.

    Args:
        daily_returns: Series of daily portfolio returns

    Returns:
        Series of drawdowns (negative values, 0 = at peak)
    """
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def calc_max_drawdown(daily_returns: pd.Series) -> float:
    """
    Calculate maximum drawdown (largest peak-to-trough decline).

    Args:
        daily_returns: Series of daily portfolio returns

    Returns:
        Max drawdown as negative decimal (-0.20 = -20%)
    """
    drawdown = calc_drawdown_series(daily_returns)
    return float(drawdown.min())


def calc_var(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Historical Value at Risk (VaR).

    VaR represents the maximum expected loss at a given confidence level.

    Args:
        daily_returns: Series of daily portfolio returns
        confidence: Confidence level (0.95 = 95%, 0.99 = 99%)

    Returns:
        VaR as negative decimal (daily, not annualized)
    """
    percentile = (1 - confidence) * 100
    return float(np.percentile(daily_returns, percentile))


def calc_cvar(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Calculate Conditional VaR (Expected Shortfall).

    CVaR is the expected loss given that the loss exceeds VaR.
    More informative than VaR as it captures tail risk.

    Args:
        daily_returns: Series of daily portfolio returns
        confidence: Confidence level (0.95 = 95%, 0.99 = 99%)

    Returns:
        CVaR as negative decimal (daily, not annualized)
    """
    var = calc_var(daily_returns, confidence)
    tail_losses = daily_returns[daily_returns <= var]
    return float(tail_losses.mean()) if len(tail_losses) > 0 else var


# =============================================================================
# TIER 2: Downside-Focused Metrics
# =============================================================================

def calc_downside_deviation(daily_returns: pd.Series, threshold: float = 0.0, annualize: bool = True) -> float:
    """
    Calculate downside deviation (semi-deviation).

    Only considers returns below the threshold (default 0).
    Better measure of risk than standard deviation for asymmetric returns.

    Args:
        daily_returns: Series of daily portfolio returns
        threshold: Minimum acceptable return (default 0)
        annualize: If True, annualize using sqrt(252)

    Returns:
        Downside deviation as decimal
    """
    downside_returns = daily_returns[daily_returns < threshold]
    if len(downside_returns) == 0:
        return 0.0

    downside_dev = float(downside_returns.std())
    return downside_dev * np.sqrt(252) if annualize else downside_dev


def calc_ulcer_index(daily_returns: pd.Series) -> float:
    """
    Calculate Ulcer Index.

    Measures both depth and duration of drawdowns.
    Formula: sqrt(mean(drawdown^2))

    Lower is better. Named because deep, prolonged drawdowns cause "ulcers".

    Args:
        daily_returns: Series of daily portfolio returns

    Returns:
        Ulcer index as decimal
    """
    drawdown = calc_drawdown_series(daily_returns)
    return float(np.sqrt((drawdown ** 2).mean()))


def calc_avg_drawdown(daily_returns: pd.Series) -> float:
    """
    Calculate average drawdown across all drawdown periods.

    A drawdown period is a contiguous sequence of underwater days.

    Args:
        daily_returns: Series of daily portfolio returns

    Returns:
        Average drawdown as negative decimal
    """
    drawdown = calc_drawdown_series(daily_returns)

    # Identify drawdown periods (contiguous sequences where drawdown < 0)
    in_drawdown = drawdown < 0

    # Find period start boundaries
    period_starts = in_drawdown & ~in_drawdown.shift(1, fill_value=False)

    # Label each period
    period_labels = period_starts.cumsum()
    period_labels[~in_drawdown] = 0

    if period_labels.max() == 0:
        return 0.0

    # Get minimum (deepest) drawdown for each period
    period_mins = drawdown.groupby(period_labels).min()
    period_mins = period_mins[period_mins.index > 0]  # Exclude non-drawdown periods

    return float(period_mins.mean()) if len(period_mins) > 0 else 0.0


def calc_avg_drawdown_duration(daily_returns: pd.Series) -> float:
    """
    Calculate average drawdown duration in trading days.

    Args:
        daily_returns: Series of daily portfolio returns

    Returns:
        Average number of days underwater
    """
    drawdown = calc_drawdown_series(daily_returns)

    in_drawdown = drawdown < 0

    # Find period boundaries
    period_starts = in_drawdown & ~in_drawdown.shift(1, fill_value=False)

    # Label each period
    period_labels = period_starts.cumsum()
    period_labels[~in_drawdown] = 0

    if period_labels.max() == 0:
        return 0.0

    # Count days in each period
    period_lengths = period_labels[period_labels > 0].groupby(period_labels[period_labels > 0]).count()

    return float(period_lengths.mean()) if len(period_lengths) > 0 else 0.0


# =============================================================================
# TIER 3: Market-Relative Metrics
# =============================================================================

def calc_beta(daily_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Calculate portfolio beta relative to benchmark.

    Beta measures systematic risk: how much the portfolio moves with the market.
    Beta = Cov(Rp, Rm) / Var(Rm)

    Args:
        daily_returns: Series of daily portfolio returns
        benchmark_returns: Series of daily benchmark returns (e.g., SPY)

    Returns:
        Beta coefficient (1.0 = moves with market, >1 = more volatile)
    """
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
    """
    Calculate tracking error (active risk).

    Measures how closely the portfolio follows the benchmark.
    Lower tracking error = more passive/index-like.

    Args:
        daily_returns: Series of daily portfolio returns
        benchmark_returns: Series of daily benchmark returns
        annualize: If True, annualize using sqrt(252)

    Returns:
        Tracking error as decimal
    """
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    excess_returns = aligned['portfolio'] - aligned['benchmark']
    te = float(excess_returns.std())

    return te * np.sqrt(252) if annualize else te


# =============================================================================
# Combined Calculation
# =============================================================================

def calc_all_risk_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None
) -> RiskMetrics:
    """
    Calculate all risk metrics for a portfolio.

    Args:
        daily_returns: Series of daily portfolio returns
        benchmark_returns: Optional benchmark returns for beta/tracking error

    Returns:
        RiskMetrics dataclass with all metrics
    """
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
    avg_drawdown = calc_avg_drawdown(daily_returns)
    avg_drawdown_duration = calc_avg_drawdown_duration(daily_returns)

    # Tier 3: Market-Relative (optional)
    beta = None
    tracking_error = None
    if benchmark_returns is not None:
        beta = calc_beta(daily_returns, benchmark_returns)
        tracking_error = calc_tracking_error(daily_returns, benchmark_returns)

    return RiskMetrics(
        volatility=volatility,
        max_drawdown=max_drawdown,
        var_95=var_95,
        var_99=var_99,
        cvar_95=cvar_95,
        cvar_99=cvar_99,
        downside_deviation=downside_deviation,
        ulcer_index=ulcer_index,
        avg_drawdown=avg_drawdown,
        avg_drawdown_duration=avg_drawdown_duration,
        beta=beta,
        tracking_error=tracking_error,
    )
