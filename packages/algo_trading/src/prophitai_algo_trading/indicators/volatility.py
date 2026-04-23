"""Volatility indicators: ATR, Bollinger, Donchian, realized vol."""

from __future__ import annotations

import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Average True Range (Wilder smoothing).

    Adds ``atr_{period}``.
    """
    df = df.copy()
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    df[f"atr_{period}"] = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    return df


def bollinger(df: pd.DataFrame, period: int = 20, stdev: float = 2.0) -> pd.DataFrame:
    """Bollinger bands.

    Adds ``bb_mid``, ``bb_upper``, ``bb_lower``, ``bb_pct_b``.
    """
    df = df.copy()

    mid = df["close"].rolling(period, min_periods=period).mean()
    std = df["close"].rolling(period, min_periods=period).std()

    upper = mid + stdev * std
    lower = mid - stdev * std

    df["bb_mid"] = mid
    df["bb_upper"] = upper
    df["bb_lower"] = lower
    df["bb_pct_b"] = (df["close"] - lower) / (upper - lower).replace(0.0, np.nan)

    return df


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Donchian channels.

    Adds ``donchian_high``, ``donchian_low``, ``donchian_mid``.
    """
    df = df.copy()

    df["donchian_high"] = df["high"].rolling(period, min_periods=period).max()
    df["donchian_low"] = df["low"].rolling(period, min_periods=period).min()
    df["donchian_mid"] = (df["donchian_high"] + df["donchian_low"]) / 2.0

    return df


def realized_vol(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Rolling close-to-close realized volatility (std of log returns).

    Adds ``realized_vol_{period}``.
    """
    df = df.copy()
    log_ret = np.log(df["close"]).diff()

    df[f"realized_vol_{period}"] = log_ret.rolling(period, min_periods=period).std()

    return df
