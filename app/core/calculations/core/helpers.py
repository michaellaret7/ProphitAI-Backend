from __future__ import annotations

from typing import Iterable, Optional, Sequence
from datetime import date

import numpy as np
import pandas as pd
from app.core.calculations.core.config import DEFAULT_SECTOR_COL, DEFAULT_WINSOR_LIMITS


# ------------------------------ Series helpers ------------------------------ #
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


def sector_zscore(df: pd.DataFrame, col: str, sector_col: str = DEFAULT_SECTOR_COL) -> pd.Series:
    """Per-sector z-score for column `col`. Falls back to global z-score if no sector.

    Returns an empty float Series if df/col are invalid.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    if sector_col not in df.columns:
        return zscore_series(df[col])
    try:
        return df.groupby(sector_col)[col].transform(zscore_series)
    except Exception:
        # Fallback to global z
        return zscore_series(df[col])


# ------------------------------ Numeric helpers ----------------------------- #
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


def pct_change(current: Optional[float], previous: Optional[float], scale: float = 1.0) -> float:
    """Percentage change (current - previous) / |previous| optionally scaled.

    Returns NaN on invalid inputs.
    """
    try:
        if current is None or previous is None:
            return np.nan
        base = safe_divide(float(current) - float(previous), abs(float(previous)))
        if np.isnan(base):
            return np.nan
        return float(base * float(scale))
    except Exception:
        return np.nan


def yoy_growth(current: Optional[float], lagged: Optional[float]) -> float:
    """Year-over-year growth: current / lagged - 1.0 (decimal)."""
    try:
        if current is None or lagged is None:
            return np.nan
        base = safe_divide(float(current), float(lagged))
        if np.isnan(base):
            return np.nan
        return float(base - 1.0)
    except Exception:
        return np.nan


# ------------------------------ Data helpers -------------------------------- #
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


# ------------------------------ Regression helper --------------------------- #
def residualize(
    df: pd.DataFrame,
    y_col: str,
    x_cols: list[str],
    out_col: str,
    *,
    zscore_y: bool = True,
    zscore_x: bool = True,
    add_const: bool = True,
) -> pd.DataFrame:
    """Compute residuals of y ~ X (optionally z-scored) and store in `out_col`.

    - Falls back to z-scored y (or original y if zscore_y=False) when regression is ill-posed.
    - Leaves df unchanged except for adding/overwriting `out_col`.
    """
    if df is None or not isinstance(df, pd.DataFrame) or y_col not in df.columns:
        return df
    # Prepare y
    y = df[y_col].astype(float)
    y_input = zscore_series(y) if zscore_y else y

    # Guard X columns
    x_list = [c for c in x_cols if c in df.columns]
    if not x_list:
        out = y_input
        out_name = out_col
        df[out_name] = out
        return df

    # Build design matrix
    X = df[x_list].astype(float).copy()
    if zscore_x:
        for c in x_list:
            X[c] = zscore_series(X[c])
    if add_const:
        X = pd.concat([pd.Series(1.0, index=X.index, name="const"), X], axis=1)

    # Align and drop NaNs
    M = pd.concat([y_input.rename("y"), X], axis=1).dropna()
    if M.empty:
        df[out_col] = y_input
        return df

    Y = M["y"].to_numpy(dtype=float)
    Xn = M.drop(columns=["y"]).to_numpy(dtype=float)
    try:
        beta, *_ = np.linalg.lstsq(Xn, Y, rcond=None)
        fitted = Xn @ beta
        resid = Y - fitted
        df[out_col] = np.nan
        df.loc[M.index, out_col] = resid
    except Exception:
        df[out_col] = y_input
    return df


# ------------------------------ Composition helper -------------------------- #
def compose_exposure(
    df: pd.DataFrame,
    cols: list[str],
    weights: dict[str, float],
    *,
    sector_col: str = DEFAULT_SECTOR_COL,
    winsor_limits: tuple[float, float] = DEFAULT_WINSOR_LIMITS,
    output_col: str = "exposure_raw",
) -> pd.DataFrame:
    """Generic pipeline: winsorize → sector z-score → weighted sum.

    - Ensures required columns exist; fills missing with NaN.
    - For each c in `cols`, creates c_w (winsorized) and c_z (sector z-score).
    - `weights` keys may be base names (e.g., 'r12_1') or z-variant names ('r12_1_z').
    - Writes weighted sum to `output_col`.
    """
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    # Ensure columns exist
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    lw, uw = winsor_limits
    # Winsorize and z-score
    for c in cols:
        df[f"{c}_w"] = winsorize_series(df[c].astype(float), lower=float(lw), upper=float(uw))
        df[f"{c}_z"] = sector_zscore(df, f"{c}_w", sector_col=sector_col)
    # Weighted sum
    out = pd.Series(0.0, index=df.index)
    for key, w in (weights or {}).items():
        zcol = key if key in df.columns else f"{key}_z"
        if zcol in df.columns:
            out = out.add(float(w) * df[zcol].fillna(0.0), fill_value=0.0)
    df[output_col] = out
    return df


