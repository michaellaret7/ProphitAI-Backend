"""Entry and exit logic for Kalman Filter Stat Arb strategy.

Regime-adaptive: trades mean-reversion when innovation variance is low
(price tracking the Kalman model) and momentum when innovation variance
is high (price deviating from the model).

Required DataFrame columns:
    kalman_z_score, kalman_slope, kalman_slope_sma, kalman_regime
"""

import pandas as pd

from prophitai_algo_trading.strategies.kalman_stat_arb.signals import (
    z_score_below_threshold,
    z_score_above_threshold,
    z_score_reverted_above,
    z_score_reverted_below,
    slope_positive,
    slope_negative,
    slope_accelerating,
    slope_decelerating,
    regime_mean_reverting,
    regime_trending,
)


def long_entry(df: pd.DataFrame, z_entry: float = 2.0) -> pd.Series:
    """Long entry: mean-reversion undervalued OR trending upward.

    Mean-reverting regime: z_score < -z_entry (price far below fair value).
    Trending regime: slope positive AND accelerating (slope > slope_sma).
    """
    mr_regime = regime_mean_reverting(df['kalman_regime'])
    mr_signal = z_score_below_threshold(df['kalman_z_score'], z_entry)

    tr_regime = regime_trending(df['kalman_regime'])
    tr_signal = (
        slope_positive(df['kalman_slope'])
        & slope_accelerating(df['kalman_slope'], df['kalman_slope_sma'])
    )

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)


def long_exit(df: pd.DataFrame, z_exit: float = 0.5) -> pd.Series:
    """Long exit: mean-reversion reverted OR trend reversed.

    Mean-reverting regime: z_score > -z_exit (price reverted toward fair value).
    Trending regime: slope turns negative.
    """
    mr_regime = regime_mean_reverting(df['kalman_regime'])
    mr_signal = z_score_reverted_above(df['kalman_z_score'], z_exit)

    tr_regime = regime_trending(df['kalman_regime'])
    tr_signal = slope_negative(df['kalman_slope'])

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)


def short_entry(df: pd.DataFrame, z_entry: float = 2.0) -> pd.Series:
    """Short entry: mean-reversion overvalued OR trending downward.

    Mean-reverting regime: z_score > z_entry (price far above fair value).
    Trending regime: slope negative AND decelerating (slope < slope_sma).
    """
    mr_regime = regime_mean_reverting(df['kalman_regime'])
    mr_signal = z_score_above_threshold(df['kalman_z_score'], z_entry)

    tr_regime = regime_trending(df['kalman_regime'])
    tr_signal = (
        slope_negative(df['kalman_slope'])
        & slope_decelerating(df['kalman_slope'], df['kalman_slope_sma'])
    )

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)


def short_exit(df: pd.DataFrame, z_exit: float = 0.5) -> pd.Series:
    """Short exit: mean-reversion reverted OR trend reversed.

    Mean-reverting regime: z_score < z_exit (price reverted toward fair value).
    Trending regime: slope turns positive.
    """
    mr_regime = regime_mean_reverting(df['kalman_regime'])
    mr_signal = z_score_reverted_below(df['kalman_z_score'], z_exit)

    tr_regime = regime_trending(df['kalman_regime'])
    tr_signal = slope_positive(df['kalman_slope'])

    return (mr_regime & mr_signal) | (tr_regime & tr_signal)
