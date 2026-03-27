from prophitai_algo_trading.strategies.ichimoku_cross.signals import (
    price_above_cloud,
    price_below_cloud,
    bullish_cross,
    bearish_cross,
)
import pandas as pd

def ichimoku_long_entry(df: pd.DataFrame) -> pd.Series:
    """Bullish entry: Tenkan crosses above Kijun while price is above cloud.

    Requires columns: Close, tenkan, kijun, senkou_a, senkou_b
    """
    above_cloud = price_above_cloud(df['close'], df['senkou_a'], df['senkou_b'])
    tk_cross = bullish_cross(df['tenkan'], df['kijun'])
    return above_cloud & tk_cross

def ichimoku_long_exit(df: pd.DataFrame) -> pd.Series:
    """Exit long: Price drops below cloud.

    Requires columns: close, senkou_a, senkou_b
    """
    return price_below_cloud(df['close'], df['senkou_a'], df['senkou_b'])

def ichimoku_short_entry(df: pd.DataFrame) -> pd.Series:
    """Bearish entry: Tenkan crosses below Kijun while price is below cloud.

    Requires columns: close, tenkan, kijun, senkou_a, senkou_b
    """
    below_cloud = price_below_cloud(df['close'], df['senkou_a'], df['senkou_b'])
    tk_cross = bearish_cross(df['tenkan'], df['kijun'])
    return below_cloud & tk_cross

def ichimoku_short_exit(df: pd.DataFrame) -> pd.Series:
    """Exit short: Price rises above cloud.

    Requires columns: close, senkou_a, senkou_b
    """
    return price_above_cloud(df['close'], df['senkou_a'], df['senkou_b'])