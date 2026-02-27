"""Volume and liquidity indicators — OBV, VWMA, money flow, and illiquidity.

All returned Series have NaN rows dropped.
"""

from typing import cast

import numpy as np
import pandas as pd


# Helper function for money flow calculation
def _calc_money_flow_volume(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """Calculate money flow volume — MFM * volume.

    MFM = ((close - low) - (high - close)) / (high - low).
    Building block for CMF and A/D Line.
    """
    hl_range = (high - low).replace(0, np.nan)
    money_flow_multiplier = ((close - low) - (high - close)) / hl_range
    return cast(pd.Series, money_flow_multiplier * volume)

def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate On-Balance Volume.

    OBV accumulates volume on up-close days and subtracts on down-close days.
    Divergence between OBV trend and price trend signals accumulation/distribution.
    """
    direction = pd.Series(np.sign(close.diff()), index=close.index)
    # Reason: first value has no prior close, set direction to 0 to avoid NaN propagation.
    direction.iloc[0] = 0
    result = cast(pd.Series, (direction * volume).cumsum())
    return result.dropna()


def calc_vwma(close: pd.Series, volume: pd.Series, window: int = 20) -> pd.Series:
    """Calculate Volume-Weighted Moving Average.

    VWMA = sum(close * volume, window) / sum(volume, window).
    When price > VWMA, heavy-volume days had higher prices — institutional
    money supports the move. When price < VWMA, institutions are selling.
    Common windows: 20, 50, 200.
    """
    cv = close * volume
    result = cast(
        pd.Series,
        cv.rolling(window=window, min_periods=window).sum()
        / volume.rolling(window=window, min_periods=window).sum(),
    )
    return result.dropna()


def calc_cmf(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> pd.Series:
    """Calculate Chaikin Money Flow (-1 to +1).

    CMF = sum(money_flow_volume, window) / sum(volume, window).
    Positive = buying pressure, negative = selling pressure.
    """
    money_flow_volume = _calc_money_flow_volume(high, low, close, volume)

    result = cast(
        pd.Series,
        money_flow_volume.rolling(window=window, min_periods=window).sum()
        / volume.rolling(window=window, min_periods=window).sum(),
    )
    return result.dropna()


def calc_accumulation_distribution(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """Calculate Accumulation/Distribution Line.

    AD = cumsum(money_flow_multiplier * volume).
    Divergence from price signals institutional accumulation or distribution.
    """
    money_flow_volume = _calc_money_flow_volume(high, low, close, volume)
    return cast(pd.Series, money_flow_volume.cumsum().dropna())


def calc_mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calculate Money Flow Index (0-100).

    MFI is volume-weighted RSI — applies RSI logic to money flow instead of
    price. Combines price momentum with volume confirmation.
    MFI > 80 = overbought with heavy volume. MFI < 20 = oversold with heavy volume.
    """
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume

    positive_flow = raw_money_flow.where(typical_price > typical_price.shift(1), 0.0)
    negative_flow = raw_money_flow.where(typical_price < typical_price.shift(1), 0.0)

    positive_sum = cast(
        pd.Series,
        positive_flow.rolling(window=window, min_periods=window).sum(),
    )
    negative_sum = cast(
        pd.Series,
        negative_flow.rolling(window=window, min_periods=window).sum(),
    )

    money_ratio = positive_sum / negative_sum.replace(0, np.nan)
    mfi = cast(pd.Series, 100 - (100 / (1 + money_ratio)))

    return mfi.dropna()


def calc_amihud_illiquidity(
    close: pd.Series,
    volume: pd.Series,
    window: int = 21,
) -> pd.Series:
    """Calculate rolling Amihud Illiquidity Ratio.

    ILLIQ = mean(|return| / dollar_volume, window).
    Higher values = less liquid, larger price impact per dollar traded.
    Common window: 21 days (1 month).
    """
    daily_returns = close.pct_change().abs()
    dollar_volume = (close * volume).replace(0, np.nan)
    ratio = daily_returns / dollar_volume

    return cast(pd.Series, ratio.rolling(window=window, min_periods=window).mean().dropna())


def calc_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> pd.Series:
    """Calculate rolling Volume-Weighted Average Price.

    VWAP = sum(typical_price * volume, window) / sum(volume, window).
    Typical price = (high + low + close) / 3.
    Price above VWAP = bullish bias, below = bearish bias.
    Institutional benchmark — traders compare execution price to VWAP.
    """
    typical_price = (high + low + close) / 3
    tp_vol = typical_price * volume

    result = cast(
        pd.Series,
        tp_vol.rolling(window=window, min_periods=window).sum()
        / volume.rolling(window=window, min_periods=window).sum(),
    )
    return result.dropna()
