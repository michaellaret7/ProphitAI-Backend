"""Trend indicators — moving averages and regression-based trend signals.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd


def calc_sma(close: pd.Series, window: int = 20) -> pd.Series:
    """Calculate Simple Moving Average.

    SMA = mean(close, window). Commonly used windows: 20, 50, 100, 200.
    """
    result = cast(pd.Series, close.rolling(window=window, min_periods=window).mean())
    return result.dropna()


def calc_ema(close: pd.Series, span: int = 20) -> pd.Series:
    """Calculate Exponential Moving Average.

    EMA applies exponentially decaying weights, reacting faster to recent
    price changes than SMA. Common spans: 12, 20, 26, 50, 200.
    """
    result = cast(pd.Series, close.ewm(span=span, adjust=False).mean())
    return result.dropna()


def calc_linear_regression(
    close: pd.Series,
    window: int = 50,
) -> tuple[pd.Series, pd.Series]:
    """Calculate rolling linear regression slope and R-squared.

    Slope measures trend direction and steepness.
    R-squared measures trend quality (how well a linear trend fits).
    High R² + steep slope = high-quality trend.

    Returns:
        (slope, r_squared)
    """
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    slopes: list[float] = []
    r_squareds: list[float] = []
    indices: list = []

    values = close.values
    index = close.index

    for i in range(window - 1, len(values)):
        y = values[i - window + 1: i + 1].astype(float)
        if np.isnan(y).any():
            continue

        y_mean = y.mean()
        cov_xy = ((x - x_mean) * (y - y_mean)).sum()
        slope = cov_xy / x_var

        y_var = ((y - y_mean) ** 2).sum()
        r_sq = (cov_xy ** 2) / (x_var * y_var) if y_var != 0 else 0.0

        slopes.append(slope)
        r_squareds.append(r_sq)
        indices.append(index[i])

    slope_series = pd.Series(slopes, index=indices, dtype=float)
    r_sq_series = pd.Series(r_squareds, index=indices, dtype=float)

    return slope_series, r_sq_series
