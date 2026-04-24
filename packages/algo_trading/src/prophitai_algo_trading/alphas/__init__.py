"""Built-in ``AlphaModel`` implementations plus the shared base classes.

Every alpha satisfies the ``AlphaModel`` protocol (``name``, ``lookback``,
``update(ctx) -> list[Insight]``). New alphas should subclass one of
the three bases below rather than implement ``update`` from scratch;
the base owns Insight construction so the per-alpha contract stays
consistent across the framework.

Base classes (pick the one that matches your signal's semantics):

    PerSymbolAlpha
        Score each ticker from its own history alone. Default choice.
        Examples: MomentumAlpha, BreakoutAlpha, ShortTermReversalAlpha,
        TrendVolumeAlpha.

    CrossSectionalAlpha
        Score each ticker against universe-wide stats (median, rank,
        percentile). Example: LowVolAlpha.

    PairAlpha
        Score ticker *pairs* for stat arb; each firing pair emits two
        Insights (long leg + short leg). Example: CointegrationPairAlpha.

If none of the three fits, implement ``AlphaModel`` (the Protocol in
``core.protocols``) directly — inheritance is optional.
"""

from prophitai_algo_trading.alphas.base import (
    CrossSectionalAlpha,
    PairAlpha,
    PerSymbolAlpha,
)
from prophitai_algo_trading.alphas.breakout import BreakoutAlpha
from prophitai_algo_trading.alphas.cointegration_pair import (
    CointegrationPairAlpha,
)
from prophitai_algo_trading.alphas.low_vol import LowVolAlpha
from prophitai_algo_trading.alphas.momentum import MomentumAlpha
from prophitai_algo_trading.alphas.reversal import ShortTermReversalAlpha
from prophitai_algo_trading.alphas.trend_volume import TrendVolumeAlpha

__all__ = [
    # Base classes (for agent-authored alphas)
    "CrossSectionalAlpha",
    "PairAlpha",
    "PerSymbolAlpha",
    # Built-in alphas
    "BreakoutAlpha",
    "CointegrationPairAlpha",
    "LowVolAlpha",
    "MomentumAlpha",
    "ShortTermReversalAlpha",
    "TrendVolumeAlpha",
]
