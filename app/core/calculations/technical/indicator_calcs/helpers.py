"""Shared helper functions for technical indicators."""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def wilder_ma(series: pd.Series, period: int) -> pd.Series:
    """Wilder's Moving Average (smoothing with alpha = 1/period)."""
    alpha = 1.0 / float(period)
    return series.ewm(alpha=alpha, adjust=False).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate True Range for ATR and other indicators."""
    prev_close = close.shift(1)
    high_low = high - low
    high_prev_close = (high - prev_close).abs()
    low_prev_close = (low - prev_close).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return tr
