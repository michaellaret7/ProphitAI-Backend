"""Trend indicators: SMA and EMA."""

from __future__ import annotations

import pandas as pd


def sma(df: pd.DataFrame, period: int, column: str = "close", name: str | None = None) -> pd.DataFrame:
    """Simple moving average.

    Adds column ``name`` (default ``sma_{period}``) to ``df``.
    """
    df = df.copy()
    out = name or f"sma_{period}"

    df[out] = df[column].rolling(period, min_periods=period).mean()

    return df


def ema(df: pd.DataFrame, period: int, column: str = "close", name: str | None = None) -> pd.DataFrame:
    """Exponential moving average.

    Adds column ``name`` (default ``ema_{period}``) to ``df``.
    """
    df = df.copy()
    out = name or f"ema_{period}"

    df[out] = df[column].ewm(span=period, adjust=False).mean()

    return df
