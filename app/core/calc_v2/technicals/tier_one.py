"""Tier 1 technical indicators — basic building blocks.

All functions accept pandas Series/DataFrames of daily OHLCV data
and return a pd.Series of indicator values aligned to the input index.
"""

from typing import cast

import numpy as np
import pandas as pd


def calc_sma(close: pd.Series, window: int = 20) -> pd.Series:
    """Calculate Simple Moving Average.

    SMA = mean(close, window). Commonly used windows: 20, 50, 100, 200.
    """
    result = close.rolling(window=window, min_periods=window).mean()
    return cast(pd.Series, result)


def calc_ema(close: pd.Series, span: int = 20) -> pd.Series:
    """Calculate Exponential Moving Average.

    EMA applies exponentially decaying weights, reacting faster to recent
    price changes than SMA. Common spans: 12, 20, 26, 50, 200.
    """
    result = close.ewm(span=span, adjust=False).mean()
    return cast(pd.Series, result)


def calc_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int | None = None,
) -> pd.Series:
    """Calculate Volume-Weighted Average Price.

    VWAP = cumsum(typical_price * volume) / cumsum(volume).
    If window is provided, uses a rolling window instead of cumulative.
    """
    typical_price = (high + low + close) / 3
    tp_vol = typical_price * volume

    if window is None:
        return cast(pd.Series, tp_vol.cumsum() / volume.cumsum())

    return cast(
        pd.Series,
        tp_vol.rolling(window=window, min_periods=window).sum()
        / volume.rolling(window=window, min_periods=window).sum(),
    )


def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume.

    OBV accumulates volume on up-close days and subtracts on down-close days.
    Divergence between OBV trend and price trend signals accumulation/distribution.
    """
    direction = pd.Series(np.sign(close.diff()), index=close.index)
    # Reason: first value has no prior close, set direction to 0 to avoid NaN propagation.
    direction.iloc[0] = 0
    return cast(pd.Series, (direction * volume).cumsum())


def calc_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Average True Range.

    ATR = EMA(true_range, window) where true_range captures gaps.
    Measures volatility in price units. Common window: 14.
    """
    prev_close = close.shift(1)
    true_range = cast(
        pd.Series,
        pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1),
    )
    result = true_range.ewm(span=window, adjust=False).mean()
    return cast(pd.Series, result)
