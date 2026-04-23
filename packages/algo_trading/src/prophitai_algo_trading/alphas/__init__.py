"""Built-in AlphaModel implementations.

Each alpha satisfies the ``AlphaModel`` protocol (``name``, ``lookback``,
``update(ctx) -> list[Insight]``). New alphas land here; tests under
``packages/algo_trading/tests/`` exercise them on real OHLCV data.
"""

from prophitai_algo_trading.alphas.breakout import BreakoutAlpha
from prophitai_algo_trading.alphas.low_vol import LowVolAlpha
from prophitai_algo_trading.alphas.momentum import MomentumAlpha
from prophitai_algo_trading.alphas.reversal import ShortTermReversalAlpha
from prophitai_algo_trading.alphas.trend_volume import TrendVolumeAlpha

__all__ = [
    "BreakoutAlpha",
    "LowVolAlpha",
    "MomentumAlpha",
    "ShortTermReversalAlpha",
    "TrendVolumeAlpha",
]
