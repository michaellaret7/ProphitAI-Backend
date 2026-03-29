"""Entry and exit logic for the Opening Range Breakout strategy.

Uses the first 15-minute bar's high/low as breakout levels, with
VWAP directional bias and volume confirmation for entries. Exits via
chandelier trailing stop, profit target, or hard stop. No time exit —
positions persist across days if the trend continues.
"""

import pandas as pd

from prophitai_algo_trading.strategies.orb_breakout.signals import (
    breaks_above_or_high,
    breaks_below_or_low,
    not_opening_bar,
    opening_range_valid,
    volume_confirmed,
    price_above_vwap,
    price_below_vwap,
    time_filter_ok,
    close_below_chandelier_long,
    close_above_chandelier_short,
    hit_profit_target_long,
    hit_profit_target_short,
    close_below_or_low,
    close_above_or_high,
)


def long_entry(df: pd.DataFrame) -> pd.Series:
    """Long entry: OR high breakout with VWAP + volume confirmation.

    Confluence required:
    1. Not the opening bar itself
    2. Opening range is valid (meets minimum ATR-based height)
    3. Close breaks above the opening range high
    4. Price above VWAP (institutional buying bias)
    5. Volume > 1.2x average (breakout confirmation)
    6. Within morning trading session (strongest ORB alpha)
    """
    return (
        not_opening_bar(df)
        & opening_range_valid(df)
        & breaks_above_or_high(df)
        & price_above_vwap(df)
        & volume_confirmed(df, threshold=1.2)
        & time_filter_ok(df)
    )


def long_exit(df: pd.DataFrame) -> pd.Series:
    """Long exit: chandelier stop, profit target, or hard stop.

    Layered exit:
    1. Hit profit target (OR high + N * OR range)
    2. Close below chandelier trailing stop (intraday high - N*ATR)
    3. Close below OR low (hard stop — full reversal)

    Reason: no time exit allows positions to persist across days,
    capturing overnight gap profit on strong trends.
    """
    profit = hit_profit_target_long(df)
    chandelier = close_below_chandelier_long(df) & not_opening_bar(df)
    hard_stop = close_below_or_low(df)
    return profit | chandelier | hard_stop


def short_entry(df: pd.DataFrame) -> pd.Series:
    """Short entry: OR low breakdown with VWAP + volume confirmation."""
    return (
        not_opening_bar(df)
        & opening_range_valid(df)
        & breaks_below_or_low(df)
        & price_below_vwap(df)
        & volume_confirmed(df, threshold=1.2)
        & time_filter_ok(df)
    )


def short_exit(df: pd.DataFrame) -> pd.Series:
    """Short exit: chandelier stop, profit target, or hard stop."""
    profit = hit_profit_target_short(df)
    chandelier = close_above_chandelier_short(df) & not_opening_bar(df)
    hard_stop = close_above_or_high(df)
    return profit | chandelier | hard_stop
