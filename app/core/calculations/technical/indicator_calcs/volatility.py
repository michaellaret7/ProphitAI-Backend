"""Volatility and channel technical indicators."""

from __future__ import annotations

import pandas as pd

from .helpers import ema, sma, wilder_ma, true_range


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder)."""
    tr = true_range(df["high"], df["low"], df["close"])
    atr = wilder_ma(tr, period)
    atr.name = f"atr_{period}"
    return atr


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands (SMA-based).

    Middle = SMA(period)
    Upper = Middle + num_std * rolling_std
    Lower = Middle - num_std * rolling_std
    """
    close = df["close"]
    middle = sma(close, period)
    rolling_std = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + num_std * rolling_std
    lower = middle - num_std * rolling_std

    out = pd.DataFrame({
        "bb_middle": middle,
        "bb_upper": upper,
        "bb_lower": lower,
    })
    return out


def calculate_donchian_channels(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Donchian Channels over lookback period.

    upper = rolling max(high), lower = rolling min(low), middle = (upper + lower)/2
    """
    high = df["high"]
    low = df["low"]
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2.0
    out = pd.DataFrame({
        "donchian_upper": upper,
        "donchian_middle": middle,
        "donchian_lower": lower,
    })
    return out


def calculate_keltner_channels(
    df: pd.DataFrame, period: int = 20, atr_period: int | None = None, multiplier: float = 2.0
) -> pd.DataFrame:
    """Keltner Channels using EMA and ATR.

    middle = EMA(close, period)
    upper = middle + multiplier * ATR(atr_period or period)
    lower = middle - multiplier * ATR(atr_period or period)
    """
    if atr_period is None:
        atr_period = period
    close = df["close"]
    middle = ema(close, period)
    atr_vals = calculate_atr(df, atr_period)
    upper = middle + multiplier * atr_vals
    lower = middle - multiplier * atr_vals
    out = pd.DataFrame({
        "keltner_middle": middle,
        "keltner_upper": upper,
        "keltner_lower": lower,
    })
    return out


def calculate_ichimoku_cloud(
    df: pd.DataFrame,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
) -> pd.DataFrame:
    """Ichimoku Cloud - Comprehensive Japanese indicator system.

    Components:
    - Tenkan-sen (Conversion Line): (9-period high + low) / 2
    - Kijun-sen (Base Line): (26-period high + low) / 2
    - Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted forward 26 periods
    - Senkou Span B (Leading Span B): (52-period high + low) / 2, shifted forward 26 periods
    - Chikou Span (Lagging Span): Current close, shifted back 26 periods

    The cloud is formed between Senkou Span A and B.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Tenkan-sen (Conversion Line)
    tenkan_high = high.rolling(window=tenkan_period, min_periods=tenkan_period).max()
    tenkan_low = low.rolling(window=tenkan_period, min_periods=tenkan_period).min()
    tenkan_sen = (tenkan_high + tenkan_low) / 2.0

    # Kijun-sen (Base Line)
    kijun_high = high.rolling(window=kijun_period, min_periods=kijun_period).max()
    kijun_low = low.rolling(window=kijun_period, min_periods=kijun_period).min()
    kijun_sen = (kijun_high + kijun_low) / 2.0

    # Senkou Span A (Leading Span A) - shifted forward
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2.0).shift(displacement)

    # Senkou Span B (Leading Span B) - shifted forward
    senkou_b_high = high.rolling(window=senkou_b_period, min_periods=senkou_b_period).max()
    senkou_b_low = low.rolling(window=senkou_b_period, min_periods=senkou_b_period).min()
    senkou_span_b = ((senkou_b_high + senkou_b_low) / 2.0).shift(displacement)

    # Chikou Span (Lagging Span) - shifted backward
    chikou_span = close.shift(-displacement)

    out = pd.DataFrame({
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a,
        "senkou_span_b": senkou_span_b,
        "chikou_span": chikou_span,
    })
    return out


def calculate_highs_lows(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Rolling highest high and lowest low over the lookback window."""
    high = df["high"]
    low = df["low"]
    hh = high.rolling(window=period, min_periods=period).max()
    ll = low.rolling(window=period, min_periods=period).min()
    out = pd.DataFrame({"rolling_high": hh, "rolling_low": ll})
    return out
