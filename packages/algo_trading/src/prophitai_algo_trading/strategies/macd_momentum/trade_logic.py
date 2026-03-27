"""Entry and exit logic for MACD Momentum strategy.

Combines MACD/signal crossovers with zero-line filter for entries.
Catches momentum reversals: long when MACD crosses up from below zero,
short when MACD crosses down from above zero.
"""

import pandas as pd

from prophitai_algo_trading.strategies.macd_momentum.signals import (
    macd_crosses_above_signal,
    macd_crosses_below_signal,
    macd_below_zero,
    macd_above_zero,
)


def long_entry(df: pd.DataFrame) -> pd.Series:
    """Long entry: MACD crosses above signal while in bearish territory.

    Catches bullish momentum reversals — strongest signal when MACD
    turns positive from negative territory.

    Requires columns: macd, macd_signal
    """
    crossover = macd_crosses_above_signal(df['macd'], df['macd_signal'])
    bearish_territory = macd_below_zero(df['macd'])
    return crossover & bearish_territory


def long_exit(df: pd.DataFrame) -> pd.Series:
    """Long exit: MACD crosses below signal (momentum fading).

    Requires columns: macd, macd_signal
    """
    return macd_crosses_below_signal(df['macd'], df['macd_signal'])


def short_entry(df: pd.DataFrame) -> pd.Series:
    """Short entry: MACD crosses below signal while in bullish territory.

    Catches bearish momentum reversals — strongest signal when MACD
    turns negative from positive territory.

    Requires columns: macd, macd_signal
    """
    crossover = macd_crosses_below_signal(df['macd'], df['macd_signal'])
    bullish_territory = macd_above_zero(df['macd'])
    return crossover & bullish_territory


def short_exit(df: pd.DataFrame) -> pd.Series:
    """Short exit: MACD crosses above signal (downward momentum fading).

    Requires columns: macd, macd_signal
    """
    return macd_crosses_above_signal(df['macd'], df['macd_signal'])
