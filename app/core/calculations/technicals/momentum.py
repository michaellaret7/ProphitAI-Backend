"""Momentum indicators — oscillators, trend strength, and momentum signals.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd

from app.core.calculations.config import TRADING_DAYS
from app.core.calculations.technicals.trend import calc_ema
from app.core.calculations.technicals.volatility import calc_true_range


def calc_roc(close: pd.Series, window: int = 252, skip_recent: int = 21) -> pd.Series:
    """Calculate Rate of Change / Momentum factor.

    ROC = (close_t-skip - close_t-window) / close_t-window.
    Default is 12-month momentum (252 days) excluding the most recent month
    (21 days) to avoid short-term reversal — the standard academic momentum
    factor (Jegadeesh & Titman, Carhart). One of the most validated factors
    in finance.
    """
    lagged_end = close.shift(skip_recent)
    lagged_start = close.shift(window)
    result = cast(pd.Series, (lagged_end - lagged_start) / lagged_start)
    return result.dropna()


def calc_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (0-100).

    RSI = 100 - 100 / (1 + avg_gain / avg_loss).
    Uses Wilder's smoothing (EMA with alpha = 1/window).
    """
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = (-delta).clip(lower=0)

    avg_gain = gains.ewm(alpha=1 / window, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = cast(pd.Series, 100 - (100 / (1 + rs)))

    return rsi.dropna()


def calc_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_span: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, signal line, and histogram.

    MACD = EMA(fast) - EMA(slow).
    Signal = EMA(MACD, signal_span).
    Histogram = MACD - Signal.

    Returns:
        (macd_line, signal_line, histogram)
    """
    macd_line = calc_ema(close, span=fast) - calc_ema(close, span=slow)
    signal_line = calc_ema(macd_line, span=signal_span)
    histogram = macd_line - signal_line

    return macd_line.dropna(), signal_line.dropna(), histogram.dropna()


def calc_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Average Directional Index (0-100).

    Measures trend strength regardless of direction.
    ADX < 20 = no trend, > 25 = trending, > 40 = strong trend.
    Uses Wilder's smoothing (EMA with alpha = 1/window).
    """
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    # Directional movement
    plus_dm = (high - prev_high).clip(lower=0)
    minus_dm = (prev_low - low).clip(lower=0)

    # Reason: only keep the larger directional move; zero out the smaller.
    plus_dm = cast(pd.Series, plus_dm.where(plus_dm > minus_dm, 0.0))
    minus_dm = cast(pd.Series, minus_dm.where(minus_dm > plus_dm, 0.0))

    true_range = calc_true_range(high, low, close)

    # Wilder's smoothing (alpha = 1/window)
    alpha = 1 / window
    atr = true_range.ewm(alpha=alpha, adjust=False).mean()
    smooth_plus = plus_dm.ewm(alpha=alpha, adjust=False).mean()
    smooth_minus = minus_dm.ewm(alpha=alpha, adjust=False).mean()

    plus_di = 100 * smooth_plus / atr.replace(0, np.nan)
    minus_di = 100 * smooth_minus / atr.replace(0, np.nan)

    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan) * 100
    adx = dx.ewm(alpha=alpha, adjust=False).mean()

    return cast(pd.Series, adx.dropna())


def calc_risk_adj_momentum(
    close: pd.Series,
    r12_window: int = 252,
    r6_window: int = 126,
    skip_recent: int = 21,
) -> pd.Series:
    """Calculate risk-adjusted momentum: (r12_1 + r6_1) / (2 × annualized vol).

    AQR-style normalization — penalizes high-volatility momentum so that
    a 20% return on 15% vol scores higher than 20% on 40% vol.

    Args:
        close: Adjusted close price series.
        r12_window: 12-month lookback window. Default 252.
        r6_window: 6-month lookback window. Default 126.
        skip_recent: Days to skip (short-term reversal). Default 21.

    Returns:
        Series of risk-adjusted momentum values.
    """
    r12 = calc_roc(close, window=r12_window, skip_recent=skip_recent)
    r6 = calc_roc(close, window=r6_window, skip_recent=skip_recent)

    daily_returns = close.pct_change()
    # Reason: use r12 window for vol to match the longest momentum horizon
    realized_vol = cast(
        pd.Series,
        daily_returns.rolling(window=r12_window, min_periods=r12_window).std() * np.sqrt(TRADING_DAYS),
    )

    # Reason: align all three series before combining
    combined = pd.concat([r12.rename('r12'), r6.rename('r6'), realized_vol.rename('vol')], axis=1).dropna()
    result = cast(
        pd.Series,
        (combined['r12'] + combined['r6']) / (2.0 * combined['vol'].replace(0, np.nan)),
    )
    return result.dropna()


def calc_time_series_momentum(
    close: pd.Series,
    lookback: int = 252,
    vol_window: int = 60,
) -> pd.Series:
    """Calculate time-series momentum signal (absolute trend following).

    Signal = sign(trailing_return) * (1 / realized_vol).
    If trailing return is positive, go long; if negative, go short.
    Position sized by inverse realized volatility (volatility targeting).
    Based on Moskowitz, Ooi, Pedersen (2012) — AQR's foundational signal.

    Args:
        close: Adjusted close price series.
        lookback: Trailing return lookback in days. Default 252 (12 months).
        vol_window: Rolling window for vol scaling. Default 60 days.

    Returns:
        Series of vol-scaled momentum signals.
    """
    daily_returns = close.pct_change()
    trailing_return = close.pct_change(periods=lookback)
    realized_vol = cast(
        pd.Series,
        daily_returns.rolling(window=vol_window, min_periods=vol_window).std() * np.sqrt(TRADING_DAYS),
    )

    signal = cast(
        pd.Series,
        np.sign(trailing_return) / realized_vol.replace(0, np.nan),
    )
    return signal.dropna()


def calc_momentum_acceleration(
    close: pd.Series,
    roc_window: int = 20,
    accel_window: int = 20,
) -> pd.Series:
    """Calculate momentum acceleration — second derivative of price.

    Acceleration = ROC(t) - ROC(t - accel_window).
    Positive = momentum speeding up. Negative = momentum fading.
    Detects turning points before standard momentum.
    """
    roc = close.pct_change(periods=roc_window)
    acceleration = cast(pd.Series, roc - roc.shift(accel_window))

    return acceleration.dropna()
