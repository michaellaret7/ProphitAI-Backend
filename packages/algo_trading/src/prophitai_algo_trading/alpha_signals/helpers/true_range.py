"""True Range — the foundation of ATR, ADX, and squeeze indicators.

True Range is the largest of:

    high - low
    |high - prev_close|
    |low  - prev_close|

This module exposes two flavors:

    true_range_series — single-ticker DataFrame with ``high``/``low``/``close``
    true_range_panel  — panel-wide ``[date x ticker]`` DataFrames for
                        ``high`` / ``low`` / ``close``
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range_series(df: pd.DataFrame) -> pd.Series:
    """True Range as a 1-D series for a single-ticker DataFrame.

    Args:
        df: DataFrame with ``high``, ``low``, ``close`` columns.

    Returns:
        Series of true-range values aligned to ``df.index``.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    range_hl = high - low
    range_hc = (high - prev_close).abs()
    range_lc = (low - prev_close).abs()

    return np.maximum(np.maximum(range_hl, range_hc), range_lc)


def true_range_panel(
    high: pd.DataFrame,
    low: pd.DataFrame,
    close: pd.DataFrame,
) -> pd.DataFrame:
    """True Range as a panel ``[date x ticker]``.

    Args:
        high: ``[date x ticker]`` panel of bar highs.
        low: ``[date x ticker]`` panel of bar lows.
        close: ``[date x ticker]`` panel of bar closes (used for ``prev_close``).

    Returns:
        DataFrame of true-range values aligned to the input panels.
    """
    prev_close = close.shift(1)

    range_hl = high - low
    range_hc = (high - prev_close).abs()
    range_lc = (low - prev_close).abs()

    return np.maximum(np.maximum(range_hl, range_hc), range_lc)
