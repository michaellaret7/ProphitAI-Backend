"""Volume-based technical indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price using typical price.

    vwap = cumsum(typical_price * volume) / cumsum(volume)
    typical_price = (high + low + close) / 3
    """
    if "volume" not in df.columns:
        raise ValueError("VWAP requires 'volume' column in dataframe")
    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]
    typical_price = (high + low + close) / 3.0
    cum_tpv = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum().replace(0.0, np.nan)
    vwap = cum_tpv / cum_vol
    vwap.name = "vwap"
    return vwap


def calculate_obv(df: pd.DataFrame) -> pd.Series:
    """On Balance Volume (OBV) - Cumulative volume-based momentum indicator.

    Calculation:
    - If close > prev_close: OBV = prev_OBV + volume
    - If close < prev_close: OBV = prev_OBV - volume
    - If close == prev_close: OBV = prev_OBV

    Used to measure buying and selling pressure. Volume trends often precede price movements.
    """
    if "volume" not in df.columns:
        raise ValueError("OBV requires 'volume' column in dataframe")

    close = df["close"]
    volume = df["volume"]

    # Determine direction: 1 if up, -1 if down, 0 if unchanged
    direction = np.sign(close.diff())

    # OBV is cumulative sum of signed volume
    obv = (direction * volume).cumsum()
    obv.name = "obv"
    return obv


def calculate_chaikin_money_flow(df: pd.DataFrame, period: int = 21) -> pd.Series:
    """Chaikin Money Flow (CMF) - Measures buying/selling pressure.

    Steps:
    1. Money Flow Multiplier = [(Close - Low) - (High - Close)] / (High - Low)
    2. Money Flow Volume = Multiplier × Volume
    3. CMF = Sum of Money Flow Volume (period) / Sum of Volume (period)

    Returns values between -1 and +1. Positive indicates buying pressure,
    negative indicates selling pressure.
    """
    if "volume" not in df.columns:
        raise ValueError("CMF requires 'volume' column in dataframe")

    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    # Money Flow Multiplier
    mf_multiplier = ((close - low) - (high - close)) / (high - low).replace(0.0, np.nan)

    # Money Flow Volume
    mf_volume = mf_multiplier * volume

    # CMF calculation
    cmf = (
        mf_volume.rolling(window=period, min_periods=period).sum()
        / volume.rolling(window=period, min_periods=period).sum().replace(0.0, np.nan)
    )
    cmf.name = f"cmf_{period}"
    return cmf
