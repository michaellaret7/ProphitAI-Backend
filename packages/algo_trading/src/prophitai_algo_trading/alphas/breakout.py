"""Donchian channel breakout alpha.

Where is the current close sitting inside its trailing N-day high/low
channel? Maps the channel position to [-0.5, +0.5]:

    position = (close - low_N) / (high_N - low_N) - 0.5

  +0.5 => new N-day high (maximum up-breakout)
  -0.5 => new N-day low  (maximum down-breakout)
   0.0 => mid-channel (no directional information)

Orthogonal to pure momentum because it measures *position within a range*
rather than *return magnitude*. A stock up 5% for the week can still sit
mid-channel if prior volatility was wide.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alphas.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class BreakoutAlpha(PerSymbolAlpha):
    """Position within the trailing close-price high-low channel.

    Args:
        lookback_days: Channel window (default 20 trading days).
        hold_days: Informational ``close_time`` horizon — breakout
            signals decay fast, so keep this shorter than momentum.
    """

    name = "breakout"

    def __init__(
        self,
        lookback_days: int = 20,
        hold_days: int = 3,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self.lookback = lookback_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        window = closes.iloc[-self._window:]

        channel_high = float(window.max())
        channel_low = float(window.min())

        span = channel_high - channel_low

        if span <= 0.0:
            return None

        current = float(closes.iloc[-1])

        return (current - channel_low) / span - 0.5

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized Donchian channel position across the full panel.

        Position within the trailing N-bar high/low channel:
            (close - rolling_min) / (rolling_max - rolling_min) - 0.5
        Rows where the channel collapses (high == low) emit NaN.
        """
        closes = panel.close

        channel_high = closes.rolling(self._window).max()
        channel_low = closes.rolling(self._window).min()

        span = channel_high - channel_low

        # Reason: zero-span rows go NaN — degenerate channel produces
        # no actionable signal.
        span = span.where(span > 0.0)

        return (closes - channel_low) / span - 0.5
