"""Signal model for the strategy scaffold."""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.signals import BaseSignalModel, cross_above, cross_below


class TemplateSignalModel(BaseSignalModel):
    """Editable entry and exit logic for the scaffold strategy.

    Replace the entry/exit/scoring logic below with your strategy's
    signal rules. Use shared signal primitives from
    ``prophitai_algo_trading.signals`` (cross_above, cross_below,
    bars_since, cooldown_mask, etc.) to compose conditions.
    """

    required_columns = ("ema_fast", "ema_slow", "rsi", "trend_gap")

    def __init__(
        self,
        rsi_long_entry_threshold: float,
        rsi_short_entry_threshold: float,
        allow_shorts: bool = True,
    ) -> None:
        self.rsi_long_entry_threshold = rsi_long_entry_threshold
        self.rsi_short_entry_threshold = rsi_short_entry_threshold
        self.allow_shorts = allow_shorts

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        """Enter long when trend turns up and RSI confirms momentum."""
        trend_bullish = cross_above(df["ema_fast"], df["ema_slow"])
        rsi_confirms = df["rsi"] >= self.rsi_long_entry_threshold
        return trend_bullish & rsi_confirms

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        """Exit longs on bearish cross or loss of RSI support.

        NOTE: rsi < 50 is intentionally aggressive — replace with a
        threshold that suits your strategy's holding period.
        """
        trend_bearish = cross_below(df["ema_fast"], df["ema_slow"])
        return trend_bearish | (df["rsi"] < 50.0)

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        """Enter short when trend turns down and RSI confirms weakness."""
        if not self.allow_shorts:
            return pd.Series(False, index=df.index)
        trend_bearish = cross_below(df["ema_fast"], df["ema_slow"])
        rsi_confirms = df["rsi"] <= self.rsi_short_entry_threshold
        return trend_bearish & rsi_confirms

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        """Exit shorts on bullish cross or loss of downside momentum.

        NOTE: rsi > 50 is intentionally aggressive — replace with a
        threshold that suits your strategy's holding period.
        """
        if not self.allow_shorts:
            return pd.Series(False, index=df.index)
        trend_bullish = cross_above(df["ema_fast"], df["ema_slow"])
        return trend_bullish | (df["rsi"] > 50.0)

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Rank entries by trend separation plus RSI distance from neutral.

        NOTE: This is a placeholder formula. Replace with a
        domain-appropriate scoring function that normalizes its inputs
        to a comparable scale.
        """
        self.validate(df)
        trend_strength = df["trend_gap"].abs() * 100.0
        momentum_strength = (df["rsi"] - 50.0).abs() / 10.0
        return (trend_strength + momentum_strength).fillna(0.0)
