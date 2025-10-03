from __future__ import annotations

from typing import Iterable, Optional, Sequence, List
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import logging
from app.core.calculations.core.config import DEFAULT_SECTOR_COL, DEFAULT_WINSOR_LIMITS, DEFAULT_TRADING_DAYS
from app.repositories.price_data import fetch_bulk_price_data_for_tickers, get_dividends_series
from app.core.calculations.returns.calculator import ReturnsCalculator

logger = logging.getLogger(__name__)

# ------------------------------ Date filtering helpers ------------------------------ #
def filter_rows_by_cutoff_date(rows: List, cutoff_date: date) -> List:
    """Filter fundamental data rows to only include those on or before cutoff_date.

    Args:
        rows: List of fundamental data rows with 'date' attribute
        cutoff_date: date object representing the cutoff

    Returns:
        Filtered list of rows
    """
    if not rows:
        return []
    filtered = []
    for r in rows:
        try:
            d = getattr(r, 'date', None)
            if d is None:
                continue
            # Handle both datetime.date and datetime.datetime objects
            dd = d.date() if hasattr(d, 'date') and callable(d.date) else d
            if dd is not None and dd <= cutoff_date:
                filtered.append(r)
        except Exception:
            continue
    return filtered

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


# ------------------------------ Returns DataFrame builders ------------------------------ #
def build_returns_df_from_price_map(
    price_map: dict[str, pd.Series],
    *,
    drop_rows: str = 'any',  # 'any' | 'all' | 'none'
    include_dividends: bool = False,
    dividends_map: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    """Build a per-ticker daily returns DataFrame from a mapping of close price Series.

    - Cleans indices to datetime and drops invalid dates per series.
    - Computes price-only or total returns per ticker.
    - Replaces inf with NaN and drops NaNs within each series.
    - drop_rows:
        'any'  -> drop rows with any NaNs across tickers (stable covariance/optimization)
        'all'  -> drop rows where all tickers are NaN (retain partial overlap)
        'none' -> keep all rows (pairwise methods handle NaNs)
    """
    if not price_map:
        return pd.DataFrame()

    returns_map: dict[str, pd.Series] = {}
    for ticker, prices in (price_map or {}).items():
        if prices is None:
            continue
        try:
            s = pd.Series(prices).astype(float)
            if s.empty:
                continue
            s.index = pd.to_datetime(s.index, errors='coerce')
            s = s[s.index.notna()]
            if s.empty:
                continue
            if include_dividends:
                divs = None if dividends_map is None else dividends_map.get(ticker)
                r = ReturnsCalculator.total_returns(s, divs)
            else:
                r = ReturnsCalculator.daily_price_returns(s)
            if r is None:
                continue
            r = pd.Series(r).replace([np.inf, -np.inf], np.nan).dropna().astype(float)
            if not r.empty:
                returns_map[ticker] = r
        except Exception:
            continue

    if not returns_map:
        return pd.DataFrame()

    df = pd.concat(returns_map, axis=1)
    if drop_rows == 'any':
        df = df.dropna(how='any')
    elif drop_rows == 'all':
        df = df.dropna(how='all')
    # else 'none': keep NaNs for pairwise-compatible methods
    return df


def build_returns_df_for_dates(
    tickers: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    include_dividends: bool = False,
    drop_rows: str = 'any',
) -> pd.DataFrame:
    """Fetch closes for tickers in [start_date, end_date] and build a returns DataFrame.

    - Delegates to `build_returns_df_from_price_map` after fetching prices (and divs if needed).
    - Applies the same cleaning and drop_rows policy.
    """
    if not tickers:
        return pd.DataFrame()

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    tickers_norm = [t.strip().upper() for t in tickers if isinstance(t, str) and t.strip()]
    price_map = fetch_bulk_price_data_for_tickers(tickers_norm, start_date_str, end_date_str, frequency='daily')

    dividends_map: dict[str, pd.Series] | None = None
    if include_dividends:
        dividends_map = {}
        for t in tickers_norm:
            try:
                divs = get_dividends_series(t, start_date, end_date)
            except Exception:
                divs = pd.Series(dtype=float)
            dividends_map[t] = divs

    return build_returns_df_from_price_map(
        price_map,
        drop_rows=drop_rows,
        include_dividends=include_dividends,
        dividends_map=dividends_map,
    )


# ------------------------------ Returns DataFrame helpers ------------------------------ #
def returns_df(tickers: list[str], lookback_years: int) -> pd.DataFrame:
    """Create a DataFrame of daily simple returns for `tickers` over `lookback_years`.

    - Skips tickers with insufficient data or non-finite returns.
    - Drops NaN/inf values per series to avoid contaminating the DataFrame.
    """
    if not tickers or lookback_years is None or int(lookback_years) <= 0:
        return pd.DataFrame()

    start_date = datetime.now() - timedelta(days=int(lookback_years) * 365)
    end_date = datetime.now()

    # Use the generalized date-range builder; retain rows with at least one non-NaN
    return build_returns_df_for_dates(
        tickers,
        start_date,
        end_date,
        include_dividends=False,
        drop_rows='all',
    )


if __name__ == "__main__":
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX', 'INTC']
    returns_data = returns_df(tickers, 2)
    print(returns_data)
