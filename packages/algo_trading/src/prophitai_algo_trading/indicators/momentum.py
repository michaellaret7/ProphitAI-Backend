"""Momentum indicators: RSI, MACD, ROC, ADX."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Relative Strength Index (Wilder smoothing).

    Adds ``rsi_{period}`` to ``df``.
    """
    df = df.copy()
    delta = df["close"].diff()

    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df[f"rsi_{period}"] = 100.0 - (100.0 / (1.0 + rs))
    df[f"rsi_{period}"] = df[f"rsi_{period}"].fillna(100.0).where(avg_gain.notna(), other=np.nan)

    return df


def macd(
    df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9,
) -> pd.DataFrame:
    """MACD line, signal, and histogram.

    Adds ``macd``, ``macd_signal``, ``macd_hist``.
    """
    df = df.copy()

    fast_ema = df["close"].ewm(span=fast, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False).mean()

    df["macd"] = fast_ema - slow_ema
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def roc(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
    """Rate of change (percent).

    Adds ``roc_{period}``.
    """
    df = df.copy()
    df[f"roc_{period}"] = df["close"].pct_change(periods=period) * 100.0

    return df


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average Directional Index (Wilder).

    Adds ``adx_{period}``, ``+di_{period}``, ``-di_{period}``.
    """
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    atr_series = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr_series
    minus_di = 100.0 * minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr_series

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)

    df[f"adx_{period}"] = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    df[f"+di_{period}"] = plus_di
    df[f"-di_{period}"] = minus_di

    return df
