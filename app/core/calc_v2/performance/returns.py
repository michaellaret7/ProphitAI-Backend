"""Return calculations — annualized, cumulative, alpha, and trailing momentum."""

import pandas as pd

from app.core.calc_v2.config import DEFAULT_RF_ANNUAL, TRADING_DAYS
from app.core.calc_v2.risk.benchmark import calc_beta


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
    rf_annual: float = DEFAULT_RF_ANNUAL,
) -> float | None:
    """Calculate Jensen's Alpha (CAPM-based).

    a = Rp - [Rf + B * (Rm - Rf)]
    Where Rp and Rm are annualized returns.
    Returns None if beta cannot be computed.
    """
    beta = calc_beta(daily_returns, benchmark_returns)
    if beta is None:
        return None

    rp = calc_annualized_return(daily_returns)
    rm = calc_annualized_return(benchmark_returns)

    expected_return = rf_annual + beta * (rm - rf_annual)
    return float(rp - expected_return)


def calc_momentum(daily_returns: pd.Series, months: int) -> float | None:
    """Calculate trailing momentum (total return) for a given number of months.

    Uses ~21 trading days per month. Returns annualized CAGR for periods > 12 months.
    Returns None if insufficient data for the requested period.
    """
    trading_days = months * 21
    if len(daily_returns) < trading_days:
        return None

    period_returns = daily_returns.iloc[-trading_days:]
    total_return = float((1 + period_returns).prod() - 1)

    # Annualize for periods > 1 year
    if months > 12:
        years = months / 12
        total_return = float((1 + total_return) ** (1 / years) - 1)

    return total_return
