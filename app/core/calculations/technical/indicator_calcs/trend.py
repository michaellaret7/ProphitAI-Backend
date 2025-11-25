"""Trend technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .helpers import ema, wilder_ma, true_range


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average Directional Index with +DI and -DI (Wilder).

    - Compute +DM and -DM from high/low diffs
    - Smooth +DM, -DM, TR with Wilder MA to get +DI and -DI
    - ADX = Wilder MA of DX = 100 * |+DI - -DI| / (+DI + -DI)
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)

    tr = true_range(high, low, close)
    atr = wilder_ma(tr, period)

    plus_di = 100.0 * wilder_ma(plus_dm, period) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * wilder_ma(minus_dm, period) / atr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di.subtract(minus_di).abs()) / (plus_di + minus_di)
    adx = wilder_ma(dx, period)

    out = pd.DataFrame({
        "+di": plus_di,
        "-di": minus_di,
        "adx": adx,
    })
    return out


def calculate_parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2) -> pd.Series:
    """Parabolic SAR implementation (PSAR).

    step: acceleration factor increment (default 0.02)
    max_step: maximum acceleration factor (default 0.2)
    Returns a Series named 'psar'.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(close)
    psar = np.full(n, np.nan, dtype=float)
    if n == 0:
        return pd.Series(psar, index=df.index, name="psar")
    if n < 3:
        # Not enough data to compute SAR reliably
        return pd.Series(psar, index=df.index, name="psar")

    # Initialize trend based on first two closes
    uptrend = close[1] > close[0]
    ep = high[0] if uptrend else low[0]
    af = step
    psar[1] = low[0] if uptrend else high[0]

    for i in range(2, n):
        prev_psar = psar[i - 1]
        if np.isnan(prev_psar):
            prev_psar = low[i - 1] if uptrend else high[i - 1]
        psar[i] = prev_psar + af * (ep - prev_psar)

        if uptrend:
            # Clamp to recent lows
            psar[i] = min(psar[i], low[i - 1], low[i - 2])
            # New extreme point?
            if high[i] > ep:
                ep = high[i]
                af = min(af + step, max_step)
            # Trend reversal?
            if low[i] < psar[i]:
                uptrend = False
                psar[i] = ep
                ep = low[i]
                af = step
        else:
            # Clamp to recent highs
            psar[i] = max(psar[i], high[i - 1], high[i - 2])
            # New extreme point?
            if low[i] < ep:
                ep = low[i]
                af = min(af + step, max_step)
            # Trend reversal?
            if high[i] > psar[i]:
                uptrend = True
                psar[i] = ep
                ep = high[i]
                af = step

    return pd.Series(psar, index=df.index, name="psar")


def calculate_bull_bear_power(df: pd.DataFrame, period: int = 13) -> pd.DataFrame:
    """Elder's Bull and Bear Power using EMA(period)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    ema_line = ema(close, period)
    bull = high - ema_line
    bear = low - ema_line
    out = pd.DataFrame({"bull_power": bull, "bear_power": bear})
    return out


def calculate_supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
    """Supertrend - Trend-following indicator based on ATR.

    Calculation:
    - hl2 = (high + low) / 2
    - upperBand = hl2 + (multiplier × ATR)
    - lowerBand = hl2 - (multiplier × ATR)

    The indicator tracks the appropriate band based on trend direction.
    Returns supertrend line and trend direction (1=uptrend, -1=downtrend).

    Default: ATR period=10, multiplier=3.0
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Calculate ATR
    tr = true_range(high, low, close)
    atr_vals = wilder_ma(tr, atr_period)
    atr_vals.name = f"atr_{atr_period}"

    # HL2 (average of high and low)
    hl2 = (high + low) / 2.0

    # Calculate basic bands
    basic_upper = hl2 + (multiplier * atr_vals)
    basic_lower = hl2 - (multiplier * atr_vals)

    # Initialize arrays for final bands and trend
    n = len(df)
    final_upper = pd.Series(np.nan, index=df.index)
    final_lower = pd.Series(np.nan, index=df.index)
    supertrend = pd.Series(np.nan, index=df.index)
    trend = pd.Series(np.nan, index=df.index)

    for i in range(atr_period, n):
        # Final upper band
        if i == atr_period or np.isnan(final_upper.iloc[i - 1]):
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = (
                basic_upper.iloc[i]
                if basic_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]
                else final_upper.iloc[i - 1]
            )

        # Final lower band
        if i == atr_period or np.isnan(final_lower.iloc[i - 1]):
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = (
                basic_lower.iloc[i]
                if basic_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]
                else final_lower.iloc[i - 1]
            )

        # Determine trend and supertrend value
        if i == atr_period:
            trend.iloc[i] = 1 if close.iloc[i] > final_upper.iloc[i] else -1
        else:
            if trend.iloc[i - 1] == 1:
                trend.iloc[i] = -1 if close.iloc[i] <= final_lower.iloc[i] else 1
            else:
                trend.iloc[i] = 1 if close.iloc[i] >= final_upper.iloc[i] else -1

        supertrend.iloc[i] = final_lower.iloc[i] if trend.iloc[i] == 1 else final_upper.iloc[i]

    out = pd.DataFrame({
        "supertrend": supertrend,
        "trend": trend,  # 1 = uptrend, -1 = downtrend
        "upper_band": final_upper,
        "lower_band": final_lower,
    })
    return out
