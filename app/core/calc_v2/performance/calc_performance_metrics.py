"""Performance metrics calculation functions for portfolio analysis."""

import numpy as np
import pandas as pd

from app.core.calc_v2.models.performance_model import PerformanceMetrics
from app.core.calc_v2.risk.calc_risk_metrics import calc_beta


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_RF_ANNUAL = 0.045  # 10-Year UST yield (~4.5%)
TRADING_DAYS = 252


# =============================================================================
# TIER 1: Core Returns
# =============================================================================

def calc_annualized_return(daily_returns: pd.Series) -> float:
    """Calculate annualized return (CAGR) from daily returns."""
    n_days = len(daily_returns)
    if n_days == 0:
        return 0.0
    cumulative = (1 + daily_returns).prod()
    n_years = n_days / TRADING_DAYS
    return float(cumulative ** (1 / n_years) - 1) if n_years > 0 else 0.0

def calc_cumulative_total_return(daily_returns: pd.Series) -> float:
    """Calculate cumulative total return over the full period."""
    return float((1 + daily_returns).prod() - 1)

def calc_alpha(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate Jensen's Alpha (CAPM-based).

    α = Rp - [Rf + β * (Rm - Rf)]
    Where Rp and Rm are annualized returns.
    """
    beta = calc_beta(daily_returns, benchmark_returns)
    rp = calc_annualized_return(daily_returns)
    rm = calc_annualized_return(benchmark_returns)

    expected_return = rf_annual + beta * (rm - rf_annual)
    return float(rp - expected_return)


# =============================================================================
# TIER 2: Risk-Adjusted Ratios
# =============================================================================

def calc_sharpe_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate annualized Sharpe Ratio.

    Sharpe = (Rp - Rf) / σp, annualized via sqrt(252).
    """
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = daily_returns - rf_daily
    mean_excess = float(excess_returns.mean())
    std = float(daily_returns.std())

    if std == 0:
        return 0.0

    return (mean_excess / std) * np.sqrt(TRADING_DAYS)


def calc_sortino_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate annualized Sortino Ratio.

    Sortino = (Rp - Rf) / Downside Deviation
    Uses downside deviation (returns below rf) instead of total volatility.
    """
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = daily_returns - rf_daily

    # Downside returns only (below threshold)
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return 0.0

    downside_dev = float(np.sqrt((downside_returns ** 2).mean()))

    if downside_dev == 0:
        return 0.0

    mean_excess = float(excess_returns.mean())
    return (mean_excess / downside_dev) * np.sqrt(TRADING_DAYS)


def calc_calmar_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate Calmar Ratio.

    Calmar = (Annualized Return - Rf) / |Max Drawdown|
    """
    ann_return = calc_annualized_return(daily_returns)

    # Max drawdown
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = abs(float(drawdown.min()))

    if max_dd == 0:
        return 0.0

    return (ann_return - rf_annual) / max_dd


def calc_information_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series
) -> float:
    """Calculate Information Ratio.

    IR = Mean(Rp - Rb) / Tracking Error
    Measures excess return per unit of active risk.
    """
    aligned = pd.DataFrame({
        'portfolio': daily_returns,
        'benchmark': benchmark_returns
    }).dropna()

    if len(aligned) < 2:
        return 0.0

    excess = aligned['portfolio'] - aligned['benchmark']
    te = float(excess.std())

    if te == 0:
        return 0.0

    return float(excess.mean() / te) * np.sqrt(TRADING_DAYS)


def calc_treynor_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate annualized Treynor Ratio.

    Treynor = (Rp - Rf) / Beta
    Measures excess return per unit of systematic risk.
    """
    beta = calc_beta(daily_returns, benchmark_returns)
    if beta == 0:
        return 0.0

    ann_return = calc_annualized_return(daily_returns)
    return (ann_return - rf_annual) / beta


def calc_omega_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> float:
    """Calculate Omega Ratio.

    Omega = Sum(returns above threshold) / |Sum(returns below threshold)|
    Threshold is the risk-free rate converted to daily.
    Captures all moments of the distribution (Keating & Shadwick 2002).
    """
    # Convert annual threshold to daily
    threshold_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1

    returns_less_thresh = daily_returns - threshold_daily

    numer = float(returns_less_thresh[returns_less_thresh > 0].sum())
    denom = float(-1.0 * returns_less_thresh[returns_less_thresh < 0].sum())

    if denom == 0:
        return 0.0

    return numer / denom


# =============================================================================
# TIER 3: Momentum Metrics
# =============================================================================

def calc_momentum(daily_returns: pd.Series, months: int) -> float:
    """Calculate trailing momentum (total return) for a given number of months.

    Uses ~21 trading days per month. Returns annualized CAGR for periods > 12 months.
    """
    trading_days = months * 21
    if len(daily_returns) < trading_days:
        return 0.0

    period_returns = daily_returns.iloc[-trading_days:]
    total_return = float((1 + period_returns).prod() - 1)

    # Annualize for periods > 1 year
    if months > 12:
        years = months / 12
        total_return = float((1 + total_return) ** (1 / years) - 1)

    return total_return


# =============================================================================
# Combined Calculation
# =============================================================================

def calc_all_performance_metrics(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    rf_annual: float = DEFAULT_RF_ANNUAL
) -> PerformanceMetrics:
    """Calculate all performance metrics for a portfolio. Returns a PerformanceMetrics instance."""
    # Tier 1: Core Returns
    annualized_return = calc_annualized_return(daily_returns)
    cumulative_total_return = calc_cumulative_total_return(daily_returns)

    # Tier 2: Risk-Adjusted Ratios
    sharpe_ratio = calc_sharpe_ratio(daily_returns, rf_annual)
    sortino_ratio = calc_sortino_ratio(daily_returns, rf_annual)
    calmar_ratio = calc_calmar_ratio(daily_returns, rf_annual)
    omega_ratio = calc_omega_ratio(daily_returns, rf_annual)

    # Tier 3: Market-Relative (optional)
    alpha = None
    information_ratio = None
    treynor_ratio = None
    if benchmark_returns is not None:
        alpha = calc_alpha(daily_returns, benchmark_returns, rf_annual)
        information_ratio = calc_information_ratio(daily_returns, benchmark_returns)
        treynor_ratio = calc_treynor_ratio(daily_returns, benchmark_returns, rf_annual)

    # Tier 4: Momentum
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
        momentum_1m=momentum_1m,
        momentum_3m=momentum_3m,
        momentum_6m=momentum_6m,
        momentum_1yr=momentum_1yr,
        momentum_3yr=momentum_3yr,
        momentum_5yr=momentum_5yr,
    )
