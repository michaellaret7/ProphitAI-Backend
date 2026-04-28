"""Narrow Range 7 (NR7) alpha — bar-level vol compression pre-breakout.

Toby Crabel (1990, *Day Trading with Short-Term Price Patterns*)
documented that bars with the smallest true range over the past N
sessions are statistically followed by larger-than-average moves.

The classic NR7 fires when today's bar has the smallest range over the
past 7 days. The signal value is the *direction the bar leaned* — sign
of the close minus the open, scaled by how compressed the range is
relative to its 7-day average:

    is_nr7    = (high - low) == min((high - low) over past 7 bars)
    direction = sign(close - open)
    score     = is_nr7 * direction * (avg_range_7 - range_today) / avg_range_7

Score is non-zero only on NR7 bars and points the way the bar's
internal price action leaned. Discrete pattern signal — orthogonal to
all the continuous alphas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class NarrowRange7Alpha(PerSymbolAlpha):
    """Crabel NR7 pre-breakout pattern signed by intra-bar lean.

    Args:
        window: Number of bars over which "narrow" is judged
            (default 7 — Crabel's original).
        hold_days: Informational ``close_time`` horizon. Crabel's edge
            plays out over 1-3 days.
    """

    name = "nr7"
    required_columns = ("open", "high", "low", "close")

    def __init__(
        self,
        window: int = 7,
        hold_days: int = 2,
    ):
        self._window = window
        self.hold_days = hold_days
        self.lookback = window

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-self._window:]

        ranges = (recent["high"] - recent["low"]).to_numpy(dtype=float)

        if len(ranges) < self._window or ranges.min() <= 0.0:
            return None

        today_range = float(ranges[-1])
        min_range = float(ranges.min())

        if today_range != min_range:
            return 0.0

        avg_range = float(ranges.mean())

        if avg_range <= 0.0:
            return None

        compression = (avg_range - today_range) / avg_range

        open_t = float(recent["open"].iloc[-1])
        close_t = float(recent["close"].iloc[-1])

        direction = 1.0 if close_t > open_t else -1.0 if close_t < open_t else 0.0

        return direction * compression

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized NR7 across the full panel."""
        if panel.high is None or panel.low is None or panel.open is None:
            raise ValueError(
                "NarrowRange7Alpha.compute_panel requires panel.open, "
                "panel.high, and panel.low",
            )

        bar_range = panel.high - panel.low

        rolling_min = bar_range.rolling(self._window).min()
        rolling_mean = bar_range.rolling(self._window).mean()

        is_nr7 = (bar_range == rolling_min).astype(float)

        compression = (rolling_mean - bar_range) / rolling_mean.where(rolling_mean > 0.0)
        compression = compression.fillna(0.0)

        direction = np.sign(panel.close - panel.open)

        return is_nr7 * direction * compression
