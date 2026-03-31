"""Shared math/statistics utilities used across execution and engine layers."""

import numpy as np
import pandas as pd


def compute_rolling_volatilities(
    ticker_closes: dict[str, pd.Series],
    window: int = 20,
    annualize_factor: float = 1.0,
) -> dict[str, float]:
    """Compute rolling volatility for each ticker from close prices.

    Args:
        ticker_closes: Mapping of ticker → close price Series.
        window: Rolling window size for std calculation.
        annualize_factor: Multiplier to annualize the per-bar std
                          (e.g. sqrt(bars_per_day * 252)). Defaults to 1.0
                          (raw per-bar std), which is sufficient when only
                          relative vol matters (e.g., inverse-vol weighting).

    Returns:
        Mapping of ticker → volatility. Tickers with insufficient
        data (fewer than 3 closes) are omitted.
    """
    vols: dict[str, float] = {}
    for ticker, closes in ticker_closes.items():
        if len(closes) < 3:
            continue
        effective_window = min(window, len(closes) - 1)
        returns = closes.pct_change(fill_method=None)
        vol = returns.rolling(effective_window, min_periods=effective_window).std().iloc[-1]
        if pd.notna(vol) and vol > 0:
            vols[ticker] = vol * annualize_factor
    return vols


def compute_rolling_volatilities_bulk(
    close_matrix: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Pre-compute rolling volatilities for all tickers across all bars.

    Vectorized version of compute_rolling_volatilities() that processes
    a full 2D close price matrix in one pass instead of per-bar recalculation.

    Args:
        close_matrix: Array of shape (n_bars, n_tickers) with close prices.
                      NaN values are tolerated (output will be NaN where
                      input has insufficient data).
        window: Rolling window size for std of returns.

    Returns:
        Array of shape (n_bars, n_tickers) with rolling volatility values.
        Rows before ``window + 1`` are NaN (insufficient data for returns + std).
    """
    n_bars, n_tickers = close_matrix.shape
    vol_matrix = np.full((n_bars, n_tickers), np.nan)

    # Reason: compute returns matrix once (n_bars - 1, n_tickers)
    with np.errstate(divide='ignore', invalid='ignore'):
        returns = np.diff(close_matrix, axis=0) / close_matrix[:-1]

    # Reason: rolling std over the returns matrix, row by row
    for i in range(window, n_bars):
        # returns[i-1] corresponds to bar i (return from bar i-1 to bar i)
        # So returns[i-window:i] gives the last `window` returns ending at bar i
        window_returns = returns[i - window:i]
        vol_matrix[i] = np.nanstd(window_returns, axis=0, ddof=1)

    return vol_matrix
