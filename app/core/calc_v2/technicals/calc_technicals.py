"""Orchestrator for computing all technical indicators on a single ticker's OHLCV data."""

import pandas as pd

from app.core.calc_v2.models.technicals_model import (
    TickerTechnicals,
    TierOneTechnicals,
)
from app.core.calc_v2.technicals.tier_one import (
    calc_atr,
    calc_ema,
    calc_obv,
    calc_sma,
    calc_vwap,
)


def calc_tier_one(ohlcv: pd.DataFrame) -> TierOneTechnicals:
    """Calculate all Tier 1 technical indicators from an OHLCV DataFrame.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].

    Returns:
        TierOneTechnicals with all indicator series.
    """
    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["adj_close"]
    volume = ohlcv["volume"]

    return TierOneTechnicals(
        sma_20=calc_sma(close, window=20),
        sma_50=calc_sma(close, window=50),
        sma_200=calc_sma(close, window=200),
        ema_12=calc_ema(close, span=12),
        ema_26=calc_ema(close, span=26),
        ema_50=calc_ema(close, span=50),
        vwap=calc_vwap(high, low, close, volume),
        obv=calc_obv(close, volume),
        atr_14=calc_atr(high, low, close, window=14),
    )


def calc_all_technicals(ohlcv: pd.DataFrame) -> TickerTechnicals:
    """Calculate all technical indicators across all tiers.

    Args:
        ohlcv: DataFrame with columns [open, high, low, adj_close, volume].
              Typically from fetch_bulk_ohlcv_data_for_tickers()[ticker].

    Returns:
        TickerTechnicals containing results from every tier.
    """
    return TickerTechnicals(
        tier_one=calc_tier_one(ohlcv),
    )
