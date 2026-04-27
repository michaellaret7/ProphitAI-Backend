"""Strategy composers — wire alpha_signals + construction + risk + execution into a strategy.

Two paradigms:

    Algorithm        — bar-driven (event-loop) strategy. Used by
                       ``engines.backtest.Backtest`` and ``engines.live.LiveRunner``.
    VectorAlgorithm  — vectorized research strategy. Used by
                       ``engines.vector_backtest.VectorBacktest`` and
                       ``analytics.alpha_isolation``.
"""

from prophitai_algo_trading.algorithm.event import Algorithm
from prophitai_algo_trading.algorithm.vector import VectorAlgorithm

__all__ = ["Algorithm", "VectorAlgorithm"]
