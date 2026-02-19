"""Drawdown metrics — series, depth, duration, and pain index."""

import numpy as np
import pandas as pd


def calc_drawdown_series(daily_returns: pd.Series) -> pd.Series:
    """Calculate the drawdown series (decline from peak) from daily returns."""
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown


def calc_max_drawdown(daily_returns: pd.Series, lookback: int | None = None) -> float:
    """Calculate maximum drawdown (largest peak-to-trough decline).

    Args:
        daily_returns: Daily return series.
        lookback: Optional trailing window in trading days. When provided,
            only the last `lookback` days are used. Defaults to None (full series).
    """
    r = daily_returns.iloc[-lookback:] if lookback is not None else daily_returns
    drawdown = calc_drawdown_series(r)
    return float(drawdown.min())


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
