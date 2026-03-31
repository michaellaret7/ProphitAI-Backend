"""Derived feature enrichment for the strategy scaffold."""

from __future__ import annotations

import pandas as pd


# ================================
# --> Sizing hint column names
# ================================
# BaseStrategy.get_sizing_hints() auto-extracts values from these
# column names when building EntryCandidate for the sizer:
#
# Volatility:  atr, atr_14, volatility, realized_vol,
#              close_to_close_vol_20, parkinson_vol_20
# Long stops:  stop_long, chandelier_long, chandelier_long_stop,
#              chandelier_stop, donchian_low, or_low
# Short stops: stop_short, chandelier_short, chandelier_short_stop,
#              donchian_high, or_high
# Regime:      regime, hurst_regime
#
# Name your derived columns using these keys and they'll flow
# automatically into the sizing pipeline via EntryCandidate.


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
