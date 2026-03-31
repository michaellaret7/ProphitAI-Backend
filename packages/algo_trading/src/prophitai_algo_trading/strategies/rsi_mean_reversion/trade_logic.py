"""Signal model for RSI Mean Reversion strategy."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.signals import BaseSignalModel
from prophitai_algo_trading.strategies.rsi_mean_reversion.signals import (
    rsi_oversold,
    rsi_overbought,
    price_above_sma,
    price_below_sma,
)


class RSIMeanReversionSignalModel(BaseSignalModel):
    """RSI mean-reversion signal model with trend-filtered entries."""

    required_columns = ("rsi", "close", "sma_trend", "sma_exit")

    def __init__(
        self,
        rsi_oversold_threshold: float = 10,
        rsi_overbought_threshold: float = 90,
    ):
        self.rsi_oversold_threshold = rsi_oversold_threshold
        self.rsi_overbought_threshold = rsi_overbought_threshold

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        """Long entry: RSI oversold while price is in an uptrend."""
        oversold = rsi_oversold(df["rsi"], threshold=self.rsi_oversold_threshold)
        uptrend = price_above_sma(df["close"], df["sma_trend"])
        return oversold & uptrend

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        """Long exit: price reverts back above the exit SMA."""
        return price_above_sma(df["close"], df["sma_exit"])

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        """Short entry: RSI overbought while price is in a downtrend."""
        overbought = rsi_overbought(df["rsi"], threshold=self.rsi_overbought_threshold)
        downtrend = price_below_sma(df["close"], df["sma_trend"])
        return overbought & downtrend

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        """Short exit: price reverts back below the exit SMA."""
        return price_below_sma(df["close"], df["sma_exit"])

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """More extreme RSI readings rank higher for fill priority."""
        return (50 - df["rsi"]).abs()
