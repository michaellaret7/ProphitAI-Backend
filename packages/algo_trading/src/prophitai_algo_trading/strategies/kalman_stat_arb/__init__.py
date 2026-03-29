"""Kalman Filter Adaptive Trend/Mean-Reversion strategy.

Uses state-space modeling (Local Linear Trend Kalman filter) to estimate
dynamic fair value, then trades mean-reversion or momentum depending on
the detected regime (innovation variance).
"""

from prophitai_algo_trading.strategies.kalman_stat_arb.strategy import KalmanStatArb
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
from prophitai_algo_trading.strategies.kalman_stat_arb.trade_logic import (
    long_entry,
    long_exit,
    short_entry,
    short_exit,
)

__all__ = [
    "KalmanStatArb",
    "z_score_below_threshold",
    "z_score_above_threshold",
    "z_score_reverted_above",
    "z_score_reverted_below",
    "slope_positive",
    "slope_negative",
    "slope_accelerating",
    "slope_decelerating",
    "regime_mean_reverting",
    "regime_trending",
    "long_entry",
    "long_exit",
    "short_entry",
    "short_exit",
]
