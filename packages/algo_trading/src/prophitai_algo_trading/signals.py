"""Signal helper primitives for strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd


def cross_above(left: pd.Series, right: pd.Series) -> pd.Series:
    """True on bars where ``left`` crosses from below to above ``right``."""
    return ((left > right) & (left.shift(1) <= right.shift(1))).fillna(False)


def cross_below(left: pd.Series, right: pd.Series) -> pd.Series:
    """True on bars where ``left`` crosses from above to below ``right``."""
    return ((left < right) & (left.shift(1) >= right.shift(1))).fillna(False)


def bars_since(event: pd.Series) -> pd.Series:
    """Count bars since the last True value; event bars themselves are 0."""
    normalized = event.fillna(False).astype(bool).to_numpy()
    values = np.full(len(normalized), np.nan)
    last_true = -1

    for idx, fired in enumerate(normalized):
        if fired:
            last_true = idx
            values[idx] = 0.0
        elif last_true >= 0:
            values[idx] = float(idx - last_true)

    return pd.Series(values, index=event.index, dtype=float)


def fired_within(event: pd.Series, lookback: int) -> pd.Series:
    """True when ``event`` fired on this bar or within the past ``lookback`` bars."""
    return bars_since(event).le(lookback).fillna(False)
