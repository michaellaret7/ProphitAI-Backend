"""Shared utility functions for calc_v2.

Pure helpers that depend only on numpy/pandas/stdlib — no internal imports.
Migrated from app.core.calculations.core.helpers to decouple calc_v2 from legacy.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd


# ================================
# --> Series helpers
# ================================

def winsorize_series(series: pd.Series, lower: float = 0.025, upper: float = 0.025) -> pd.Series:
    """Clip a Series by lower/upper quantiles (symmetric by default).

    Returns the original Series if empty or on failure.
    """
    if series is None or isinstance(series, float) and np.isnan(series):
        return series
    if not isinstance(series, pd.Series) or series.empty:
        return series
    s = series.copy()
    try:
        lo = s.quantile(float(lower))
        hi = s.quantile(1.0 - float(upper))
        return s.clip(lower=lo, upper=hi)
    except Exception:
        return s


def zscore_series(series: pd.Series) -> pd.Series:
    """Z-score a Series; returns zeros if std is 0/NaN or on degenerate input."""
    if series is None or not isinstance(series, pd.Series) or series.empty:
        return series
    s = series.astype(float).copy()
    m = s.mean()
    sd = s.std(ddof=0)
    if sd is None or sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - m) / sd


# ================================
# --> Numeric helpers
# ================================

def ttm(values: Sequence[Optional[float]] | pd.Series, window: int = 4) -> float:
    """Trailing-twelve-month style aggregator: sum of the most recent `window` values.

    - Accepts a list-like ordered most-recent-first.
    - Requires all `window` values to be non-None; otherwise returns NaN.
    """
    if values is None:
        return np.nan
    try:
        seq = list(values)
    except Exception:
        return np.nan
    if len(seq) < int(window):
        return np.nan
    try:
        vals = [float(x) for x in seq[: int(window)] if x is not None]
        if len(vals) < int(window):
            return np.nan
        return float(np.nansum(vals))
    except Exception:
        return np.nan


def safe_divide(numerator: Optional[float], denominator: Optional[float], default: float = np.nan) -> float:
    """Divide with guards on None/zero/invalid values."""
    try:
        if numerator is None or denominator is None:
            return default
        d = float(denominator)
        if d == 0.0 or np.isnan(d):
            return default
        return float(numerator) / d
    except Exception:
        return default


# ================================
# --> Data helpers
# ================================

def sort_rows_desc_by_date(rows: Optional[Iterable]) -> list:
    """Sort an iterable of objects by `.date` descending.

    Returns a list; on error returns the input coerced to list without sorting.
    """
    if not rows:
        return []
    try:
        return sorted(list(rows), key=lambda r: getattr(r, "date", None) or date.min, reverse=True)
    except Exception:
        return list(rows)
