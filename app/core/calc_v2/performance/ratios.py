"""Risk-adjusted performance ratios — Sharpe, Sortino, Calmar, IR, Treynor, Omega."""

import numpy as np
import pandas as pd

from app.core.calc_v2.config import DEFAULT_RF_ANNUAL, TRADING_DAYS
from app.core.calc_v2.performance.returns import calc_annualized_return
from app.core.calc_v2.risk.benchmark import align_returns, calc_beta
from app.core.calc_v2.risk.drawdown import calc_max_drawdown


def calc_sharpe_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate annualized Sharpe Ratio.

    Sharpe = (Rp - Rf) / sigma_p, annualized via sqrt(252).
    Returns None if zero volatility (ratio undefined).
    """
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = daily_returns - rf_daily
    mean_excess = float(excess_returns.mean())
    std = float(daily_returns.std())

    if std == 0:
        return None

    return (mean_excess / std) * np.sqrt(TRADING_DAYS)


def calc_sortino_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate annualized Sortino Ratio.

    Sortino = (Rp - Rf) / Downside Deviation
    Uses downside deviation (returns below rf) instead of total volatility.
    Returns None if no downside returns or zero downside deviation.
    """
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = daily_returns - rf_daily

    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return None

    downside_dev = float(np.sqrt((downside_returns ** 2).mean()))

    if downside_dev == 0:
        return None

    mean_excess = float(excess_returns.mean())
    return (mean_excess / downside_dev) * np.sqrt(TRADING_DAYS)


def calc_calmar_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate Calmar Ratio.

    Calmar = (Annualized Return - Rf) / |Max Drawdown|
    Returns None if no drawdown occurred (ratio undefined).
    """
    ann_return = calc_annualized_return(daily_returns)
    max_dd = abs(calc_max_drawdown(daily_returns))

    if max_dd == 0:
        return None

    return (ann_return - rf_annual) / max_dd


def calc_information_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float | None:
    """Calculate Information Ratio.

    IR = Mean(Rp - Rb) / Tracking Error
    Measures excess return per unit of active risk.
    Returns None if insufficient overlapping data or zero tracking error.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return None

    excess = aligned['portfolio'] - aligned['benchmark']
    te = float(excess.std())

    if te == 0:
        return None

    return float(excess.mean() / te) * np.sqrt(TRADING_DAYS)


def calc_treynor_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate annualized Treynor Ratio.

    Treynor = (Rp - Rf) / Beta
    Measures excess return per unit of systematic risk.
    Returns None if beta cannot be computed or is zero.
    """
    beta = calc_beta(daily_returns, benchmark_returns)
    if beta is None or beta == 0:
        return None

    ann_return = calc_annualized_return(daily_returns)
    return (ann_return - rf_annual) / beta


def calc_omega_ratio(
    daily_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate Omega Ratio.

    Omega = Sum(returns above threshold) / |Sum(returns below threshold)|
    Threshold is the risk-free rate converted to daily.
    Captures all moments of the distribution (Keating & Shadwick 2002).
    Returns None if no returns below threshold (ratio undefined).
    """
    threshold_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1

    returns_less_thresh = daily_returns - threshold_daily

    numer = float(returns_less_thresh[returns_less_thresh > 0].sum())
    denom = float(-1.0 * returns_less_thresh[returns_less_thresh < 0].sum())

    if denom == 0:
        return None

    return numer / denom


def calc_win_rate(daily_returns: pd.Series) -> float | None:
    """Calculate win rate (percentage of positive return days).

    Returns None if no observations.
    """
    if len(daily_returns) == 0:
        return None

    return float((daily_returns > 0).sum() / len(daily_returns))


def calc_profit_factor(daily_returns: pd.Series) -> float | None:
    """Calculate profit factor (gross profits / gross losses).

    Profit factor > 1.0 means profitable, > 1.5 is strong.
    Returns None if no losing days (ratio undefined).
    """
    gains = float(daily_returns[daily_returns > 0].sum())
    losses = float(daily_returns[daily_returns < 0].sum())

    if losses == 0:
        return None

    return gains / abs(losses)


def calc_gain_loss_ratio(daily_returns: pd.Series) -> float | None:
    """Calculate gain/loss ratio (average win / average loss).

    Complements win rate — a low win rate with high gain/loss ratio
    can still be profitable. Returns None if no winning or losing days.
    """
    winners = daily_returns[daily_returns > 0]
    losers = daily_returns[daily_returns < 0]

    if len(winners) == 0 or len(losers) == 0:
        return None

    return float(winners.mean() / abs(losers.mean()))


def calc_tail_ratio(daily_returns: pd.Series) -> float | None:
    """Calculate tail ratio (95th percentile / |5th percentile|).

    Measures return asymmetry. > 1.0 means the right tail is fatter
    than the left (favorable). Returns None if 5th percentile is zero.
    """
    p95 = float(daily_returns.quantile(0.95))
    p5 = float(daily_returns.quantile(0.05))

    if p5 == 0:
        return None

    return p95 / abs(p5)
