"""Relative-strength cross-sectional rank alpha.

Ranks every ticker by its N-day (default 63 bar ≈ 3 months) total
return and emits a signed score proportional to percentile position:

    rank_pct_i  = percentile of ret_i among all ready tickers, in (0, 1]
    score_i     = 2 * rank_pct_i - 1                   # -> [-1, +1]

Top-decile names get ≈+0.8 to +1.0 (longs); bottom-decile get ≈-0.8
to -1.0 (shorts); middle of the pack scores near zero. This is the
classic cross-sectional momentum factor — orthogonal to
``DollarVolumeRankAlpha`` (which tilts by size/liquidity, not return).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alphas.base import CrossSectionalAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext


class RelativeStrengthRankAlpha(CrossSectionalAlpha):
    """Cross-sectional percentile rank on N-day total return.

    Args:
        lookback_days: Return measurement window (default 63 ≈ 3M).
        hold_days: Insight close_time horizon.
        min_universe_size: Below this count of ready tickers the
            ranking is too noisy to act on.
    """

    name = "rs_rank"

    def __init__(
        self,
        lookback_days: int = 63,
        hold_days: int = 10,
        min_universe_size: int = 10,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        # Reason: need window+1 closes so the first return exists.
        self.lookback = lookback_days + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        returns: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]
            start = float(closes.iloc[-(self._window + 1)])
            end = float(closes.iloc[-1])

            if start <= 0.0 or end <= 0.0:
                continue

            returns[symbol] = (end / start) - 1.0

        if len(returns) < self._min_universe:
            return None

        symbols = list(returns.keys())
        values = np.array([returns[s] for s in symbols])

        # Reason: ordinal percentile rank — handles ties by position,
        # which is good enough for a ~3M return decile tilt.
        order = values.argsort().argsort()
        ranks = (order + 1) / len(values)  # in (0, 1]

        rank_by_symbol = {sym: float(ranks[i]) for i, sym in enumerate(symbols)}

        return {"rank_by_symbol": rank_by_symbol}

    def compute_score(
        self, symbol: str, df: pd.DataFrame, stats: dict,
    ) -> float | None:
        rank_by_symbol: dict[str, float] = stats["rank_by_symbol"]

        rank_pct = rank_by_symbol.get(symbol)

        if rank_pct is None:
            return None

        return 2.0 * rank_pct - 1.0
