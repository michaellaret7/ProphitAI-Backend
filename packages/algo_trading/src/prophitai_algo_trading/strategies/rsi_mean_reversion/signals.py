"""Pure signal functions for RSI Mean Reversion strategy.

Reusable conditions based on RSI levels and SMA relationships.
"""

import pandas as pd


def rsi_oversold(rsi: pd.Series, threshold: float = 10) -> pd.Series:
    """RSI is below the oversold threshold (extreme weakness)."""
    return rsi < threshold


def rsi_overbought(rsi: pd.Series, threshold: float = 90) -> pd.Series:
    """RSI is above the overbought threshold (extreme strength)."""
    return rsi > threshold


def price_above_sma(close: pd.Series, sma: pd.Series) -> pd.Series:
    """Price is above the moving average (bullish trend filter)."""
    return close > sma


def price_below_sma(close: pd.Series, sma: pd.Series) -> pd.Series:
    """Price is below the moving average (bearish trend filter)."""
    return close < sma
