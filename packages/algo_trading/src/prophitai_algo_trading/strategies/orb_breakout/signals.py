"""Pure signal functions for Opening Range Breakout strategy.

Atomic conditions used by trade_logic to compose entry/exit rules.
Each function returns a boolean Series aligned with the DataFrame index.
"""

import pandas as pd


# ================================
# --> Helper funcs
# ================================

def breaks_above_or_high(df: pd.DataFrame) -> pd.Series:
    """Close breaks above the opening range high (bullish breakout)."""
    return df['close'] > df['or_high']


def breaks_below_or_low(df: pd.DataFrame) -> pd.Series:
    """Close breaks below the opening range low (bearish breakdown)."""
    return df['close'] < df['or_low']


def not_opening_bar(df: pd.DataFrame) -> pd.Series:
    """Current bar is NOT the opening range bar (avoid self-reference)."""
    return ~df['is_or_bar']


def opening_range_valid(df: pd.DataFrame) -> pd.Series:
    """Opening range meets minimum ATR-based height threshold."""
    return df['or_valid'].fillna(False)


def volume_confirmed(df: pd.DataFrame, threshold: float = 1.2) -> pd.Series:
    """Breakout bar volume exceeds threshold x average volume."""
    return df['volume_ratio'] > threshold


def price_above_vwap(df: pd.DataFrame) -> pd.Series:
    """Price is above VWAP (institutional buying bias)."""
    return df['close'] > df['vwap']


def price_below_vwap(df: pd.DataFrame) -> pd.Series:
    """Price is below VWAP (institutional selling bias)."""
    return df['close'] < df['vwap']


def time_filter_ok(df: pd.DataFrame) -> pd.Series:
    """Current bar is within valid trading hours."""
    return df['time_ok'].fillna(False)


def near_market_close(df: pd.DataFrame) -> pd.Series:
    """Current bar is near market close (time to exit)."""
    return df['near_close'].fillna(False)


def close_below_chandelier_long(df: pd.DataFrame) -> pd.Series:
    """Price falls below chandelier trailing stop (for longs)."""
    return df['close'] < df['chandelier_long_stop']


def close_above_chandelier_short(df: pd.DataFrame) -> pd.Series:
    """Price rises above chandelier trailing stop (for shorts)."""
    return df['close'] > df['chandelier_short_stop']


def hit_profit_target_long(df: pd.DataFrame) -> pd.Series:
    """Price hits or exceeds long profit target."""
    return df['close'] >= df['profit_target_long']


def hit_profit_target_short(df: pd.DataFrame) -> pd.Series:
    """Price hits or falls below short profit target."""
    return df['close'] <= df['profit_target_short']


def close_below_or_low(df: pd.DataFrame) -> pd.Series:
    """Price falls below OR low (hard stop for longs)."""
    return df['close'] < df['or_low']


def close_above_or_high(df: pd.DataFrame) -> pd.Series:
    """Price rises above OR high (hard stop for shorts)."""
    return df['close'] > df['or_high']
