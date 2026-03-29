"""Entry and exit logic for RSI Mean Reversion strategy.

Combines RSI extremes with SMA trend filter for entries,
and SMA crossback for exits (mean reversion complete).
"""

import pandas as pd

from prophitai_algo_trading.strategies.rsi_mean_reversion.signals import (
    rsi_oversold,
    rsi_overbought,
    price_above_sma,
    price_below_sma,
)


def long_entry(df: pd.DataFrame, rsi_threshold: float = 10) -> pd.Series:
    """Long entry: RSI oversold while price is in an uptrend.

    Requires columns: rsi, close, sma_trend
    """
    oversold = rsi_oversold(df['rsi'], threshold=rsi_threshold)
    uptrend = price_above_sma(df['close'], df['sma_trend'])
    return oversold & uptrend


def long_exit(df: pd.DataFrame) -> pd.Series:
    """Long exit: price reverts back above the exit SMA.

    Requires columns: close, sma_exit
    """
    return price_above_sma(df['close'], df['sma_exit'])


def short_entry(df: pd.DataFrame, rsi_threshold: float = 90) -> pd.Series:
    """Short entry: RSI overbought while price is in a downtrend.

    Requires columns: rsi, close, sma_trend
    """
    overbought = rsi_overbought(df['rsi'], threshold=rsi_threshold)
    downtrend = price_below_sma(df['close'], df['sma_trend'])
    return overbought & downtrend


def short_exit(df: pd.DataFrame) -> pd.Series:
    """Short exit: price reverts back below the exit SMA.

    Requires columns: close, sma_exit
    """
    return price_below_sma(df['close'], df['sma_exit'])
