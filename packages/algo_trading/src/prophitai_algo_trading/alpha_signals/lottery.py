"""Lottery-effect alpha (MAX anomaly).

Bali, Cakici, Whitelaw (2011, JFE "Maxing Out") documented that stocks
with the *highest single-day return* over the past month systematically
underperform — investors overpay for "lottery tickets," driving them
to negative expected return after the fact.

The signal is cross-sectional: per bar, score each ticker by the
deviation of its rolling MAX from the universe median. Above-median
MAX (lottery name) gets a negative score (short candidate); below-
median (no recent extreme) gets a positive score (long candidate).

    max_i = max(daily_return_i over past N bars)
    score = median_universe_max - max_i

Distinct from low-vol because a stock's overall vol can be modest
while still carrying one extreme print. Distinct from skewness which
weights the whole distribution, not the single tail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.panel import PricePanel


class LotteryAlpha(CrossSectionalAlpha):
    """Cross-sectional MAX-anomaly score (median - max).

    Args:
        lookback_days: Window over which the per-symbol MAX is taken
            (default 21 = ~one trading month).
        hold_days: Informational ``close_time`` horizon — Bali et al
            documented monthly rebalances.
        min_universe_size: Universe-size floor for the median.
    """

    name = "lottery"

    def __init__(
        self,
        lookback_days: int = 21,
        hold_days: int = 21,
        min_universe_size: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size

        self.lookback = lookback_days + 1

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        max_by_symbol: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            returns = df["close"].pct_change().iloc[-self._window:]

            if returns.isna().all():
                continue

            max_ret = float(returns.max())

            if not np.isfinite(max_ret):
                continue

            max_by_symbol[symbol] = max_ret

        if len(max_by_symbol) < self._min_universe:
            return None

        median_max = float(np.median(list(max_by_symbol.values())))

        return {"max": max_by_symbol, "median": median_max}

    def compute_score(
        self, symbol: str, df: "pd.DataFrame", stats: dict,
    ) -> float | None:
        max_by_symbol: dict[str, float] = stats["max"]
        median_max: float = stats["median"]

        max_ret = max_by_symbol.get(symbol)

        if max_ret is None:
            return None

        return median_max - max_ret

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized cross-sectional MAX-anomaly score across the panel."""
        returns = panel.close.pct_change()

        max_panel = returns.rolling(self._window).max()

        valid_count = max_panel.count(axis=1)
        median_max = max_panel.median(axis=1)

        score = max_panel.rsub(median_max, axis=0)

        thin_rows = valid_count < self._min_universe
        score.loc[thin_rows, :] = 0.0

        return score.fillna(0.0)
