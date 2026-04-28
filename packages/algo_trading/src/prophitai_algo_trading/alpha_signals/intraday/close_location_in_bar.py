"""Close-location-in-bar alpha (intraday auction pressure).

For each hourly bar, where does the close sit inside the bar's high-
low range? Closes near the high indicate buyers won the auction;
closes near the low indicate sellers won. The signal: rolling-mean
of close-location values, smoothed over a few bars to reduce single-
bar noise.

    clv = ((C - L) - (H - C)) / (H - L)        ∈ [-1, +1]
    score = rolling_mean(clv, window)

Distinct from any return-based signal: pure intra-bar pressure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class CloseLocationInBarAlpha(PerSymbolAlpha):
    """Rolling-mean of close-location-value on hourly bars."""

    name = "close_location_in_bar"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        smoothing_window: int = 3,
        hold_days: int = 1,
    ):
        self._window = smoothing_window
        self.hold_days = hold_days
        self.lookback = smoothing_window

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-self._window:]

        high = recent["high"]
        low = recent["low"]
        close = recent["close"]

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        if len(clv) < self._window:
            return None

        return float(clv.mean())

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        if panel.high is None or panel.low is None:
            raise ValueError(
                "CloseLocationInBarAlpha.compute_panel requires panel.high "
                "and panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        return clv.rolling(self._window).mean()
