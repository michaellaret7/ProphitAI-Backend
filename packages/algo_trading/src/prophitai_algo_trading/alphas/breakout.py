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
