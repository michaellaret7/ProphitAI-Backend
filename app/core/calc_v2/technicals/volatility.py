"""Volatility indicators — ATR, range-based estimators, and Bollinger Bands.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd

from app.core.calc_v2.technicals.trend import calc_sma


def calc_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Average True Range.

    ATR = EMA(true_range, window) where true_range captures gaps.
    Measures volatility in price units. Common window: 14.
    """
    prev_close = close.shift(1)
    true_range = cast(
        pd.Series,
        pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1),
    )
    result = cast(pd.Series, true_range.ewm(span=window, adjust=False).mean())
    return result.dropna()


def calc_close_to_close_volatility(
    close: pd.Series,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """Calculate rolling close-to-close volatility.

    Rolling std of daily returns. Annualized by default via sqrt(252).
    """
    daily_returns = close.pct_change()
    vol = cast(pd.Series, daily_returns.rolling(window=window, min_periods=window).std())

    if annualize:
        vol = cast(pd.Series, vol * np.sqrt(252))

    return cast(pd.Series, vol.dropna())


# =============================================================================
# Range-Based Volatility Estimators
# =============================================================================

def calc_parkinson_volatility(
    high: pd.Series,
    low: pd.Series,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """Calculate rolling Parkinson volatility estimator.

    Uses high-low range only. 5x more efficient than close-to-close.
    Assumes zero drift and no opening gaps.
    sigma = sqrt(sum(ln(H/L)^2) / (4 * n * ln(2)))
    """
    log_hl_sq = np.log(high / low) ** 2
    raw = cast(
        pd.Series,
        log_hl_sq.rolling(window=window, min_periods=window).mean() / (4 * np.log(2)),
    )
    vol = cast(pd.Series, np.sqrt(raw))

    if annualize:
        vol = cast(pd.Series, vol * np.sqrt(252))

    return vol.dropna()


def calc_garman_klass_volatility(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """Calculate rolling Garman-Klass volatility estimator.

    Uses OHLC data. 8x more efficient than close-to-close.
    sigma^2 = (1/n) * sum(0.5 * ln(H/L)^2 - (2ln2 - 1) * ln(C/O)^2)
    """
    log_hl_sq = np.log(high / low) ** 2
    log_co_sq = np.log(close / open_) ** 2
    intraday = 0.5 * log_hl_sq - (2 * np.log(2) - 1) * log_co_sq

    variance = cast(
        pd.Series,
        intraday.rolling(window=window, min_periods=window).mean(),
    )
    vol = cast(pd.Series, np.sqrt(variance.clip(lower=0)))

    if annualize:
        vol = cast(pd.Series, vol * np.sqrt(252))

    return vol.dropna()


def calc_yang_zhang_volatility(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """Calculate rolling Yang-Zhang volatility estimator.

    Combines overnight (close-to-open), open-to-close, and Rogers-Satchell
    components. 14x more efficient than close-to-close. Handles drift and gaps.
    sigma^2 = sigma_overnight^2 + k * sigma_open^2 + (1-k) * sigma_RS^2
    where k = 0.34 / (1.34 + (n+1) / (n-1))
    """
    # Overnight return: previous close to current open
    log_oc = np.log(open_ / close.shift(1))
    # Open-to-close return
    log_co = np.log(close / open_)

    # Rogers-Satchell component (accounts for drift)
    log_hc = np.log(high / close)
    log_ho = np.log(high / open_)
    log_lc = np.log(low / close)
    log_lo = np.log(low / open_)
    rs = log_hc * log_ho + log_lc * log_lo

    # Rolling variances
    n = window
    k = 0.34 / (1.34 + (n + 1) / (n - 1))

    overnight_var = cast(pd.Series, log_oc.rolling(window=n, min_periods=n).var())
    openclose_var = cast(pd.Series, log_co.rolling(window=n, min_periods=n).var())
    rs_var = cast(pd.Series, rs.rolling(window=n, min_periods=n).mean())

    variance = overnight_var + k * openclose_var + (1 - k) * rs_var
    vol = cast(pd.Series, np.sqrt(variance.clip(lower=0)))

    if annualize:
        vol = cast(pd.Series, vol * np.sqrt(252))

    return vol.dropna()


# =============================================================================
# Bollinger Bands
# =============================================================================

def calc_bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands (upper, middle, lower).

    Middle = SMA(close, window).
    Upper/Lower = Middle ± num_std * rolling_std.

    Returns:
        (upper_band, middle_band, lower_band)
    """
    middle = calc_sma(close, window=window)
    rolling_std = cast(
        pd.Series,
        close.rolling(window=window, min_periods=window).std().dropna(),
    )

    upper = middle + num_std * rolling_std
    lower = middle - num_std * rolling_std

    return (
        cast(pd.Series, upper.dropna()),
        middle,
        cast(pd.Series, lower.dropna()),
    )


def calc_bollinger_pct_b(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """Calculate Bollinger %B — normalized position within the bands (0-1).

    %B = (close - lower) / (upper - lower).
    Values > 1 = above upper band, < 0 = below lower band.
    """
    upper, _, lower = calc_bollinger_bands(close, window, num_std)
    band_width = upper - lower
    result = (close - lower) / band_width.replace(0, np.nan)
    return cast(pd.Series, result.dropna())


def calc_bollinger_bandwidth(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """Calculate Bollinger Bandwidth — measures volatility compression/expansion.

    Bandwidth = (upper - lower) / middle.
    Low bandwidth = squeeze (impending breakout). High = expanded volatility.
    """
    upper, middle, lower = calc_bollinger_bands(close, window, num_std)
    result = (upper - lower) / middle.replace(0, np.nan)
    return cast(pd.Series, result.dropna())
