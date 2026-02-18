"""Pydantic model for technical indicator output."""

import pandas as pd
from pydantic import BaseModel, ConfigDict


class TierOneTechnicals(BaseModel):
    """Container for Tier 1 technical indicator series."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Moving Averages
    sma_20: pd.Series
    sma_50: pd.Series
    sma_200: pd.Series
    ema_12: pd.Series
    ema_26: pd.Series
    ema_50: pd.Series

    # Volume
    vwap: pd.Series
    obv: pd.Series

    # Volatility
    atr_14: pd.Series


class TickerTechnicals(BaseModel):
    """Top-level container aggregating all technical tiers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tier_one: TierOneTechnicals
