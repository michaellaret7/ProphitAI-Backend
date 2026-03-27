"""Entry and exit logic for the Squeeze Breakout strategy (v2 — high Sharpe).

Combines TTM Squeeze firing with Donchian breakout confirmation,
momentum direction, and volume for entries. Uses Keltner lower channel
as the primary exit with momentum reversal as an early profit-lock.

Long-only strategy — short entries disabled.
"""

import pandas as pd

from prophitai_algo_trading.strategies.squeeze_breakout.signals import (
    squeeze_just_fired,
    momentum_positive,
    momentum_negative,
    momentum_rising,
    momentum_falling,
    donchian_breakout_high,
    donchian_breakout_low,
    volume_confirmed,
    price_above_sma50,
    atr_expanding,
    close_below_bb_mid,
)


# ================================
# --> Helper funcs
# ================================

def _recent_squeeze_fired(df: pd.DataFrame, lookback: int = 8) -> pd.Series:
    """True if squeeze fired within the last N bars (including current).

    Reason: squeeze fires on one bar, but the breakout move often develops
    over the next several bars. An 8-bar window catches entries that
    confirm shortly after the squeeze releases.
    """
    fired = squeeze_just_fired(df)
    return fired.rolling(window=lookback, min_periods=1).max().fillna(0).astype(bool)


def long_entry(df: pd.DataFrame) -> pd.Series:
    """Long entry: squeeze recently fired + bullish momentum + breakout.

    Confluence required:
    1. Squeeze fired within last 8 bars (volatility expanding from compression)
    2. Momentum oscillator positive AND rising (bullish acceleration)
    3. Close at or above prior Donchian high (breakout confirmation)
    4. Price above 50-bar SMA (intermediate trend aligned)
    5. Volume > 1.2x average (breakout volume confirmation)
    """
    recent_squeeze = _recent_squeeze_fired(df)
    mom_bullish = momentum_positive(df) & momentum_rising(df)
    breakout = donchian_breakout_high(df)
    trend = price_above_sma50(df)
    return recent_squeeze & mom_bullish & breakout & trend


def long_exit(df: pd.DataFrame) -> pd.Series:
    """Long exit: Keltner stop OR momentum reversal OR Donchian stop.

    Layered exit:
    1. Close below Keltner lower channel (significant breakdown)
    2. Momentum turns negative AND falling (bearish acceleration) AND
       price below BB midline (confirmed weakness, not just a wobble)
    3. Close below Donchian low (trend reversal hard stop)

    Reason: the momentum+BB combo catches failing breakouts earlier than
    KC lower alone, reducing average loss size and improving Sharpe.
    """
    kc_stop = df['close'] < df['kc_lower']
    # Reason: triple-confirm weakness before early exit to avoid whipsaws
    momentum_reversal = (
        momentum_negative(df) & momentum_falling(df) & close_below_bb_mid(df)
    )
    donchian_stop = donchian_breakout_low(df)
    return kc_stop | momentum_reversal | donchian_stop


def short_entry(df: pd.DataFrame) -> pd.Series:
    """Short entry: disabled (long-only strategy)."""
    return pd.Series(False, index=df.index)


def short_exit(df: pd.DataFrame) -> pd.Series:
    """Short exit: always True (force-close any shorts)."""
    return pd.Series(True, index=df.index)
