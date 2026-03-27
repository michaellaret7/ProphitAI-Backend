"""Pure signal functions for MACD Momentum strategy.

Reusable conditions based on MACD line, signal line, and histogram.
Crossover detection reuses bullish_cross/bearish_cross from ichimoku signals.
"""

import pandas as pd

from prophitai_algo_trading.strategies.ichimoku_cross.signals import bullish_cross, bearish_cross


# ================================
# --> Helper funcs
# ================================

def macd_crosses_above_signal(macd: pd.Series, signal: pd.Series) -> pd.Series:
    """MACD line crosses above the signal line (bullish momentum shift)."""
    return bullish_cross(macd, signal)


def macd_crosses_below_signal(macd: pd.Series, signal: pd.Series) -> pd.Series:
    """MACD line crosses below the signal line (bearish momentum shift)."""
    return bearish_cross(macd, signal)


def macd_below_zero(macd: pd.Series) -> pd.Series:
    """MACD line is below zero (bearish territory)."""
    return macd < 0


def macd_above_zero(macd: pd.Series) -> pd.Series:
    """MACD line is above zero (bullish territory)."""
    return macd > 0


def histogram_positive(histogram: pd.Series) -> pd.Series:
    """MACD histogram is positive (bullish momentum expanding)."""
    return histogram > 0


def histogram_negative(histogram: pd.Series) -> pd.Series:
    """MACD histogram is negative (bearish momentum expanding)."""
    return histogram < 0
