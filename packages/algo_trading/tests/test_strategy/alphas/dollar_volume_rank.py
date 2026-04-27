"""Dollar-volume liquidity tilt alpha (cross-sectional).

Ranks the universe by recent average dollar volume and tilts toward
higher-liquidity names. Empirically, the most-traded names in a
universe earn a premium relative to their less-traded peers on a risk-
adjusted basis — a size/liquidity factor.

    dv_i          = mean(close * volume) over lookback window, per ticker
    median_dv     = cross-sectional median of dv across ready tickers
    score_i       = log(dv_i) - log(median_dv)

Positive = above-median dollar volume -> long.
Negative = below-median                -> short.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import CrossSectionalAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext


class DollarVolumeRankAlpha(CrossSectionalAlpha):
    """Log-ratio tilt toward high-dollar-volume names.

    Args:
        lookback_days: Rolling window for the dollar-volume mean.
        hold_days: Insight close_time horizon. Liquidity is a slow
            factor — longer hold than momentum/reversion.
        min_universe_size: Below this count of ready tickers, the
            median is too noisy and the alpha emits nothing.
    """

    name = "liquidity_tilt"
    required_columns = ("close", "volume")

    def __init__(
        self,
        lookback_days: int = 20,
        hold_days: int = 10,
        min_universe_size: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self._min_universe = min_universe_size
        self.lookback = lookback_days

    def compute_universe_stats(
        self, ctx: "AlgorithmContext",
    ) -> dict | None:
        dvs: dict[str, float] = {}

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            window = df.iloc[-self._window:]
            dv = float((window["close"] * window["volume"]).mean())

            if dv <= 0.0 or not np.isfinite(dv):
                continue

            dvs[symbol] = dv

        if len(dvs) < self._min_universe:
            return None

        median_dv = float(np.median(list(dvs.values())))

        if median_dv <= 0.0:
            return None

        return {"dvs": dvs, "median_dv": median_dv}

    def compute_score(
        self, symbol: str, df: pd.DataFrame, stats: dict,
    ) -> float | None:
        dvs: dict[str, float] = stats["dvs"]
        median_dv: float = stats["median_dv"]

        dv = dvs.get(symbol)

        if dv is None:
            return None

        return float(np.log(dv) - np.log(median_dv))
