"""Entry and exit logic for VWAP Hurst BTC strategy.

Regime-adaptive: trades mean-reversion when Hurst < 0.45 (price reverts to VWAP)
and momentum when Hurst > 0.55 (EMA crossover breakouts). Goes flat when
Hurst ~ 0.5 (random walk — no statistical edge).

Required DataFrame columns:
    vwap_z_score, hurst_regime, ema_fast, ema_slow
"""

import pandas as pd

from prophitai_algo_trading.strategies.vwap_hurst_btc.signals import (
    vwap_oversold,
    vwap_overbought,
    vwap_reverted_from_below,
    vwap_reverted_from_above,
    ema_bullish_cross,
    ema_bearish_cross,
    ema_fast_below_slow,
    ema_fast_above_slow,
    regime_mean_reverting,
    regime_trending,
)


def long_entry(
    df: pd.DataFrame,
    vwap_entry_mult: float = 1.5,
) -> pd.Series:
    """Long entry: VWAP reversion buy OR momentum breakout.

    Mean-reverting regime: price significantly below VWAP (z < -entry_mult).
    Trending regime: bullish EMA crossover (fast crosses above slow).
    Random walk: no entry (all False).
    """
    mr_regime = regime_mean_reverting(df['hurst_regime'])
    mr_signal = vwap_oversold(df['vwap_z_score'], vwap_entry_mult)

    tr_regime = regime_trending(df['hurst_regime'])
    tr_signal = ema_bullish_cross(df['ema_fast'], df['ema_slow'])

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)


def long_exit(
    df: pd.DataFrame,
    vwap_exit_mult: float = 0.3,
) -> pd.Series:
    """Long exit: VWAP reversion target hit OR momentum reversed.

    Mean-reverting regime: price reverted back toward VWAP (z > -exit_mult).
    Trending regime: fast EMA drops below slow EMA (trend reversal).
    Random walk: always exit (close any open position).
    """
    mr_regime = regime_mean_reverting(df['hurst_regime'])
    mr_signal = vwap_reverted_from_below(df['vwap_z_score'], vwap_exit_mult)

    tr_regime = regime_trending(df['hurst_regime'])
    tr_signal = ema_fast_below_slow(df['ema_fast'], df['ema_slow'])

    # Reason: random walk regime has no edge — force exit to preserve capital
    rw_exit = df['hurst_regime'] == 2

    return (mr_regime & mr_signal) | (tr_regime & tr_signal) | rw_exit


def short_entry(
    df: pd.DataFrame,
    vwap_entry_mult: float = 1.5,
) -> pd.Series:
    """Short entry: VWAP reversion sell OR momentum breakdown.

    Mean-reverting regime: price significantly above VWAP (z > entry_mult).
    Trending regime: bearish EMA crossover (fast crosses below slow).
    Random walk: no entry (all False).
    """
    mr_regime = regime_mean_reverting(df['hurst_regime'])
    mr_signal = vwap_overbought(df['vwap_z_score'], vwap_entry_mult)

    tr_regime = regime_trending(df['hurst_regime'])
    tr_signal = ema_bearish_cross(df['ema_fast'], df['ema_slow'])

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)


def short_exit(
    df: pd.DataFrame,
    vwap_exit_mult: float = 0.3,
) -> pd.Series:
    """Short exit: VWAP reversion target hit OR momentum reversed.

    Mean-reverting regime: price reverted back toward VWAP (z < exit_mult).
    Trending regime: fast EMA rises above slow EMA (trend reversal).
    Random walk: always exit (close any open position).
    """
    mr_regime = regime_mean_reverting(df['hurst_regime'])
    mr_signal = vwap_reverted_from_above(df['vwap_z_score'], vwap_exit_mult)

    tr_regime = regime_trending(df['hurst_regime'])
    tr_signal = ema_fast_above_slow(df['ema_fast'], df['ema_slow'])

    # Reason: random walk regime has no edge — force exit to preserve capital
    rw_exit = df['hurst_regime'] == 2

    return (mr_regime & mr_signal) | (tr_regime & tr_signal) | rw_exit
