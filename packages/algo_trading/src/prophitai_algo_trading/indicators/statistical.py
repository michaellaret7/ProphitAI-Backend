"""Statistical indicators: z-score and rolling max."""

from __future__ import annotations

import pandas as pd


def zscore(
    df: pd.DataFrame, period: int = 20, column: str = "close", name: str | None = None,
) -> pd.DataFrame:
    """Rolling z-score of ``column``.

    Adds ``name`` (default ``zscore_{column}_{period}``).
    """
    df = df.copy()
    out = name or f"zscore_{column}_{period}"

    rolling = df[column].rolling(period, min_periods=period)
    mean = rolling.mean()
    std = rolling.std()

    df[out] = (df[column] - mean) / std.replace(0.0, float("nan"))

    return df


def rolling_max(
    df: pd.DataFrame, period: int = 20, column: str = "close", name: str | None = None,
) -> pd.DataFrame:
    """Rolling maximum.

    Adds ``name`` (default ``rolling_max_{column}_{period}``).
    """
    df = df.copy()
    out = name or f"rolling_max_{column}_{period}"

    df[out] = df[column].rolling(period, min_periods=period).max()

    return df
