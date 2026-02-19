"""Return distribution metrics — volatility, downside deviation, VaR, CVaR, shape."""

import numpy as np
import pandas as pd

from app.core.calc_v2.config import TRADING_DAYS


def calc_volatility(daily_returns: pd.Series, annualize: bool = True) -> float:
    """Calculate portfolio volatility. Annualized by default using sqrt(252)."""
    vol = float(daily_returns.std())
    return vol * np.sqrt(TRADING_DAYS) if annualize else vol


def calc_downside_deviation(daily_returns: pd.Series, threshold: float = 0.0, annualize: bool = True) -> float:
    """Calculate downside deviation (semi-deviation below threshold)."""
    downside_returns = daily_returns[daily_returns < threshold]
    if len(downside_returns) == 0:
        return 0.0

    downside_dev = float(downside_returns.std())
    return downside_dev * np.sqrt(TRADING_DAYS) if annualize else downside_dev


def calc_var(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Historical Value at Risk (VaR) at given confidence level."""
    percentile = (1 - confidence) * 100
    return float(np.percentile(daily_returns, percentile))


def calc_cvar(daily_returns: pd.Series, confidence: float = 0.95) -> float:
    """Calculate Conditional VaR (Expected Shortfall) — expected loss beyond VaR."""
    var = calc_var(daily_returns, confidence)
    tail_losses = daily_returns[daily_returns <= var]
    return float(tail_losses.mean()) if len(tail_losses) > 0 else var


def calc_skewness(daily_returns: pd.Series) -> float:
    """Calculate skewness of returns distribution."""
    return float(daily_returns.skew())


def calc_kurtosis(daily_returns: pd.Series) -> float:
    """Calculate excess kurtosis of returns distribution (normal dist = 0)."""
    return float(daily_returns.kurtosis())
