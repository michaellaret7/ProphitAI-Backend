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
) -> float:
    """Calculate annualized Sharpe Ratio.

    Sharpe = (Rp - Rf) / sigma_p, annualized via sqrt(252).
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
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float:
    """Calculate annualized Sortino Ratio.

    Sortino = (Rp - Rf) / Downside Deviation
    Uses downside deviation (returns below rf) instead of total volatility.
    """
    rf_daily = rf_annual / TRADING_DAYS
    excess_returns = daily_returns - rf_daily

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
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float:
    """Calculate Calmar Ratio.

    Calmar = (Annualized Return - Rf) / |Max Drawdown|
    """
    ann_return = calc_annualized_return(daily_returns)
    max_dd = abs(calc_max_drawdown(daily_returns))

    if max_dd == 0:
        return 0.0

    return (ann_return - rf_annual) / max_dd


def calc_information_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Calculate Information Ratio.

    IR = Mean(Rp - Rb) / Tracking Error
    Measures excess return per unit of active risk.
    """
    aligned = align_returns(daily_returns, benchmark_returns)
    if aligned is None:
        return 0.0

    excess = aligned['portfolio'] - aligned['benchmark']
    te = float(excess.std())

    if te == 0:
        return 0.0

    return float(excess.mean() / te) * np.sqrt(TRADING_DAYS)


def calc_treynor_ratio(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    rf_annual: float = DEFAULT_RF_ANNUAL,
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
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float:
    """Calculate Omega Ratio.

    Omega = Sum(returns above threshold) / |Sum(returns below threshold)|
    Threshold is the risk-free rate converted to daily.
    Captures all moments of the distribution (Keating & Shadwick 2002).
    """
    threshold_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1

    returns_less_thresh = daily_returns - threshold_daily

    numer = float(returns_less_thresh[returns_less_thresh > 0].sum())
    denom = float(-1.0 * returns_less_thresh[returns_less_thresh < 0].sum())

    if denom == 0:
        return 0.0

    return numer / denom
