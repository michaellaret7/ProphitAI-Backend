"""Reusable signal primitives for multi-bar and algorithmic trade logic."""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "bars_since",
    "cooldown_mask",
    "cross_above",
    "cross_below",
    "debounce",
    "fired_within",
    "stays_above",
]


def cross_above(left: pd.Series, right: pd.Series) -> pd.Series:
    """Return True on bars where ``left`` crosses from below to above ``right``."""
    return ((left > right) & (left.shift(1) <= right.shift(1))).fillna(False)


def cross_below(left: pd.Series, right: pd.Series) -> pd.Series:
    """Return True on bars where ``left`` crosses from above to below ``right``."""
    return ((left < right) & (left.shift(1) >= right.shift(1))).fillna(False)


def bars_since(event: pd.Series) -> pd.Series:
    """Count bars since the last True value; event bars themselves are zero."""
    normalized = event.fillna(False).astype(bool)
    values = np.full(len(normalized), np.nan)
    last_true_index: int | None = None

    for idx, fired in enumerate(normalized):
        if fired:
            last_true_index = idx
            values[idx] = 0.0
        elif last_true_index is not None:
            values[idx] = float(idx - last_true_index)

    return pd.Series(values, index=normalized.index, dtype=float)


def fired_within(event: pd.Series, lookback: int) -> pd.Series:
    """Return True when ``event`` fired on the current bar or within lookback bars."""
    _validate_non_negative_bars("lookback", lookback)
    return bars_since(event).le(lookback).fillna(False)


def stays_above(left: pd.Series, right: pd.Series, bars: int) -> pd.Series:
    """Return True when ``left`` has remained above ``right`` for ``bars`` bars."""
    _validate_positive_bars("bars", bars)
    above = (left > right).fillna(False)
    if bars == 1:
        return above
    return above.rolling(bars, min_periods=bars).sum().eq(bars)


def cooldown_mask(trigger: pd.Series, bars: int) -> pd.Series:
    """Return False while a cooldown triggered by ``trigger`` is still active."""
    _validate_non_negative_bars("bars", bars)
    return ~fired_within(trigger, lookback=bars)


def debounce(signal: pd.Series, bars: int) -> pd.Series:
    """Keep the first True value, then suppress repeats for ``bars`` bars."""
    _validate_non_negative_bars("bars", bars)
    normalized = signal.fillna(False).astype(bool)
    if bars == 0:
        return normalized

    accepted = np.zeros(len(normalized), dtype=bool)
    remaining_cooldown = 0

    for idx, fired in enumerate(normalized):
        if remaining_cooldown > 0:
            remaining_cooldown -= 1
            continue
        if fired:
            accepted[idx] = True
            remaining_cooldown = bars

    return pd.Series(accepted, index=normalized.index)


def _validate_positive_bars(name: str, value: int) -> None:
    if value < 1:
        raise ValueError(f"{name} must be >= 1")


def _validate_non_negative_bars(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
