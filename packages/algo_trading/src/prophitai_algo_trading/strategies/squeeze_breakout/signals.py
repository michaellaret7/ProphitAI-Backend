"""Pure signal functions for Squeeze Breakout strategy.

Atomic conditions used by trade_logic to compose entry/exit rules.
Each function returns a boolean Series aligned with the DataFrame index.
"""

import pandas as pd


# ================================
# --> Helper funcs
# ================================

def squeeze_just_fired(df: pd.DataFrame) -> pd.Series:
    """Squeeze transitions from ON to OFF (volatility expanding)."""
    return df['squeeze_fired'].fillna(False)


def squeeze_fired_quality(df: pd.DataFrame) -> pd.Series:
    """Quality squeeze fired: lasted >= 4 bars before releasing."""
    return df['squeeze_fired_quality'].fillna(False)


def squeeze_is_on(df: pd.DataFrame) -> pd.Series:
    """Bollinger Bands are inside Keltner Channels (compression)."""
    return df['squeeze_on'].fillna(False)


def bbw_low_percentile(df: pd.DataFrame, threshold: float = 25.0) -> pd.Series:
    """BB Width is in the low percentile range (tight squeeze)."""
    return df['bbw_percentile'] < threshold


def momentum_positive(df: pd.DataFrame) -> pd.Series:
    """Squeeze momentum oscillator is above zero (bullish bias)."""
    return df['squeeze_momentum'] > 0


def momentum_negative(df: pd.DataFrame) -> pd.Series:
    """Squeeze momentum oscillator is below zero (bearish bias)."""
    return df['squeeze_momentum'] < 0


def momentum_rising(df: pd.DataFrame) -> pd.Series:
    """Momentum is increasing (accelerating in current direction)."""
    return df['squeeze_momentum'] > df['squeeze_momentum_prev']


def momentum_falling(df: pd.DataFrame) -> pd.Series:
    """Momentum is decreasing (decelerating or reversing)."""
    return df['squeeze_momentum'] < df['squeeze_momentum_prev']


def donchian_breakout_high(df: pd.DataFrame) -> pd.Series:
    """Close breaks above the prior N-period high (Donchian breakout)."""
    return df['close'] >= df['donchian_high']


def donchian_breakout_low(df: pd.DataFrame) -> pd.Series:
    """Close breaks below the prior N-period low (Donchian breakdown)."""
    return df['close'] <= df['donchian_low']


def volume_confirmed(df: pd.DataFrame, threshold: float = 1.2) -> pd.Series:
    """Current bar volume exceeds threshold x average volume."""
    return df['volume_ratio'] > threshold


def price_above_sma50(df: pd.DataFrame) -> pd.Series:
    """Price is above the 50-bar SMA (intermediate uptrend)."""
    return df['close'] > df['sma_50']


def price_below_sma50(df: pd.DataFrame) -> pd.Series:
    """Price is below the 50-bar SMA (intermediate downtrend)."""
    return df['close'] < df['sma_50']


def atr_expanding(df: pd.DataFrame) -> pd.Series:
    """ATR is above its 50-bar average (volatility expanding)."""
    return df['atr'] > df['atr_ma']


def rsi_overbought(df: pd.DataFrame, threshold: float = 75.0) -> pd.Series:
    """RSI(14) exceeds overbought threshold — mean reversion exit signal."""
    return df['rsi'] > threshold


def close_below_chandelier(df: pd.DataFrame) -> pd.Series:
    """Price falls below the Chandelier trailing stop."""
    return df['close'] < df['chandelier_stop']


def close_below_bb_mid(df: pd.DataFrame) -> pd.Series:
    """Price falls below Bollinger Band midline (momentum fading for longs)."""
    return df['close'] < df['bb_mid']


def close_above_bb_mid(df: pd.DataFrame) -> pd.Series:
    """Price rises above Bollinger Band midline (momentum fading for shorts)."""
    return df['close'] > df['bb_mid']
