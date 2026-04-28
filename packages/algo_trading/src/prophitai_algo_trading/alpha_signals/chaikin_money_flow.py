"""Chaikin Money Flow alpha.

Chaikin (1980s) measures buying / selling pressure inside the bar by
weighting the close-location-value (CLV) by volume, then averaging
over a window:

    clv = ((close - low) - (high - close)) / (high - low)   ∈ [-1, +1]
    cmf = sum_N(clv * volume) / sum_N(volume)               ∈ [-1, +1]

Positive CMF => buyers won the auction (close near highs on heavy
volume) for most of the window. Distinct from a pure volume-z signal:
this combines *intra-bar pressure* with volume, and unlike OBV's
sign-of-Δclose, CLV is continuous so it weights *how much* the close
won the bar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _close_location_value(df: "pd.DataFrame") -> "pd.Series":
    """Continuous CLV in [-1, +1]; zero-range bars become 0."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    span = high - low

    clv = ((close - low) - (high - close)) / span.where(span > 0.0)

    return clv.fillna(0.0)


#     ================================
# --> Alpha
#     ================================

class ChaikinMoneyFlowAlpha(PerSymbolAlpha):
    """Volume-weighted close-location value over a rolling window.

    Args:
        lookback_days: Smoothing window (default 20).
        hold_days: Informational ``close_time`` horizon.
    """

    name = "chaikin_money_flow"
    required_columns = ("high", "low", "close", "volume")

    def __init__(
        self,
        lookback_days: int = 20,
        hold_days: int = 10,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self.lookback = lookback_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        clv = _close_location_value(df).iloc[-self._window:]
        volume = df["volume"].iloc[-self._window:]

        total_vol = float(volume.sum())

        if total_vol <= 0.0:
            return None

        return float((clv * volume).sum()) / total_vol

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized CMF across the full panel."""
        if panel.high is None or panel.low is None or panel.volume is None:
            raise ValueError(
                "ChaikinMoneyFlowAlpha.compute_panel requires panel.high, "
                "panel.low, and panel.volume",
            )

        high = panel.high
        low = panel.low
        close = panel.close
        volume = panel.volume

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        money_flow_vol = clv * volume

        numerator = money_flow_vol.rolling(self._window).sum()
        denominator = volume.rolling(self._window).sum()

        return numerator / denominator.where(denominator > 0.0)
