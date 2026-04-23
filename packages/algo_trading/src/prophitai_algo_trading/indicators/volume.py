"""Volume indicators: VWAP and OBV."""

from __future__ import annotations

import numpy as np
import pandas as pd


def vwap(df: pd.DataFrame) -> pd.DataFrame:
    """Running session volume-weighted average price.

    This is a session-anchored running VWAP — it never resets. For daily
    resets use a strategy-local version. Adds ``vwap``.
    """
    df = df.copy()

    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_tpv = (typical * df["volume"]).cumsum()

    df["vwap"] = cum_tpv / cum_vol.replace(0.0, np.nan)

    return df


def obv(df: pd.DataFrame) -> pd.DataFrame:
    """On-balance volume.

    Adds ``obv``.
    """
    df = df.copy()

    delta = df["close"].diff()
    direction = np.sign(delta).fillna(0.0)

    df["obv"] = (direction * df["volume"]).cumsum()

    return df
