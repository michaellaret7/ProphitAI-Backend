"""Hourly range-breakout alpha (intraday momentum continuation).

When a bar's close prints at the highest level over the past N bars,
fresh demand has overwhelmed supply at that price level — momentum
typically extends into the next bar. Symmetric for new lows.

    score = +1   if close == max(close over past N bars)
            -1   if close == min(close over past N bars)
            0    otherwise

Discrete signal — fires only on fresh extremes. Distinct from Donchian
position (continuous, daily) — this is the binary breakout event at
hourly granularity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class RangeBreakoutHourlyAlpha(PerSymbolAlpha):
    """+1 on N-bar close-high, -1 on N-bar close-low, 0 otherwise."""

    name = "range_breakout_hourly"

    def __init__(
        self,
        window: int = 20,
        hold_days: int = 1,
    ):
        self._window = window
        self.hold_days = hold_days
        self.lookback = window

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df["close"].iloc[-self._window:]

        if len(recent) < self._window:
            return None

        cur = float(recent.iloc[-1])
        peak = float(recent.max())
        trough = float(recent.min())

        if cur >= peak:
            return 1.0

        if cur <= trough:
            return -1.0

        return 0.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        closes = panel.close

        rolling_high = closes.rolling(self._window).max()
        rolling_low = closes.rolling(self._window).min()

        is_new_high = (closes >= rolling_high).astype(float)
        is_new_low = (closes <= rolling_low).astype(float)

        return is_new_high - is_new_low
