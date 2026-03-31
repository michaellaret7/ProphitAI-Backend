"""Derived feature enrichment for the strategy scaffold."""

from __future__ import annotations

import pandas as pd


def add_template_indicator_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lightweight derived columns on top of the shared indicators.

    This is the simplest place for an agent to add strategy-local features
    without needing to register a new global indicator class. Operates
    in-place on the DataFrame passed from the indicator suite.
    """
    if {"ema_fast", "ema_slow", "close"}.issubset(df.columns):
        df["trend_gap"] = (
            (df["ema_fast"] - df["ema_slow"]) / df["close"]
        ).fillna(0.0)

        # Reason: placeholder stops — replace with strategy-appropriate
        # levels. Long stops should be below price, short stops above.
        df["stop_long"] = df["ema_slow"]
        df["stop_short"] = df["ema_slow"]

        regime = pd.Series("neutral", index=df.index, dtype="object")
        regime = regime.mask(df["trend_gap"] > 0, "bull_trend")
        regime = regime.mask(df["trend_gap"] < 0, "bear_trend")
        df["regime"] = regime

    if "rsi" in df.columns:
        df["rsi_centered"] = df["rsi"] - 50.0

    return df
