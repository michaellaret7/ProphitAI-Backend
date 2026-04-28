"""Close Location Value alpha — intra-bar pressure averaged over a window.

The Close Location Value (CLV) measures where the close sits inside
the bar's range, normalized to ``[-1, +1]``:

    clv = ((close - low) - (high - close)) / (high - low)

CLV = +1 ⇒ close on the high (buyers won).
CLV = -1 ⇒ close on the low  (sellers won).
CLV =  0 ⇒ close at the midpoint.

The score is a rolling mean — persistent buying pressure shows up as
an average CLV well above zero. Pure intra-bar pressure with no volume
weighting; orthogonal to ``ChaikinMoneyFlowAlpha`` which combines CLV
with volume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class CloseLocationAlpha(PerSymbolAlpha):
    """Rolling-mean of close-location-value.

    Args:
        lookback_days: Smoothing window for CLV (default 5).
        hold_days: Informational ``close_time`` horizon — short-horizon
            pressure decays quickly.
    """

    name = "close_location"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        lookback_days: int = 5,
        hold_days: int = 3,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self.lookback = lookback_days

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
        """Vectorized CLV rolling-mean across the panel."""
        if panel.high is None or panel.low is None:
            raise ValueError(
                "CloseLocationAlpha.compute_panel requires panel.high and "
                "panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        return clv.rolling(self._window).mean()
