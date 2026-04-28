"""Kaufman Efficiency Ratio alpha — net change vs. path length.

Perry Kaufman (1995, *Smarter Trading*) defined the Efficiency Ratio
as the ratio of net price change to the sum of absolute bar-to-bar
changes:

    er = |close_t - close_{t-N}| / sum_N |close_i - close_{i-1}|

ER ∈ [0, 1]. ER → 1 means price moved straight (efficient trend); ER →
0 means price moved a lot but went nowhere (chop). Multiplying by the
sign of the net change yields a directional signal that fires only
when there's a clean trend to ride:

    score = sign(close_t - close_{t-N}) * er

Distinct from MACD / SMA-ribbon trend signals — those fire on any
above/below regime; ER suppresses signals during whipsaw markets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class KaufmanEfficiencyAlpha(PerSymbolAlpha):
    """Net-change ÷ path-length, signed by net change.

    Args:
        lookback_days: ER window (default 10 — Kaufman's original).
        hold_days: Informational ``close_time`` horizon. Trends that
            score high on ER tend to persist over multiple weeks.
    """

    name = "efficiency_ratio"

    def __init__(
        self,
        lookback_days: int = 10,
        hold_days: int = 5,
    ):
        self._window = lookback_days
        self.hold_days = hold_days

        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"].iloc[-(self._window + 1):]

        if len(closes) < self._window + 1:
            return None

        net_change = float(closes.iloc[-1] - closes.iloc[0])

        path_length = float(closes.diff().abs().iloc[1:].sum())

        if path_length <= 0.0:
            return None

        er = abs(net_change) / path_length

        sign = 1.0 if net_change > 0.0 else -1.0 if net_change < 0.0 else 0.0

        return sign * er

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized Kaufman ER × sign(net change) across the panel."""
        closes = panel.close

        net_change = closes.diff(self._window)

        path_length = closes.diff().abs().rolling(self._window).sum()

        er = net_change.abs() / path_length.where(path_length > 0.0)

        return np.sign(net_change) * er
