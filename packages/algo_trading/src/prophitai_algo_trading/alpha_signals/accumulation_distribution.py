"""Accumulation/Distribution divergence alpha.

The Accumulation/Distribution line (Williams) cumulates close-location-
value-weighted volume into a running total — like OBV but with CLV
replacing sign(Δclose):

    ad_t = ad_{t-1} + clv_t * volume_t,    clv = ((C-L)-(H-C))/(H-L)

The signal is a *divergence* between the AD slope and the price slope:
when price rises while AD stagnates, distribution is happening under
the surface (institutions selling into retail buying). When price
falls while AD rises, accumulation is happening under the surface.

    score = slope_N(ad_norm) - slope_N(price_norm)

Both slopes are normalized to per-bar % change so different price /
volume scales don't dominate. Positive score => AD outpacing price
(stealth accumulation). Distinct from OBV-slope because A/D weights by
*continuous* CLV, not the sign of Δclose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _normalized_slope(series: "pd.Series", window: int) -> float:
    """Linear-regression slope of the last ``window`` values, divided by mean.

    Returns 0.0 if the series is degenerate (mean <= 0 or insufficient data).
    """
    sliced = series.iloc[-window:].to_numpy(dtype=float)

    if len(sliced) < window:
        return 0.0

    mean_v = float(np.abs(sliced).mean())

    if mean_v <= 0.0:
        return 0.0

    x = np.arange(window, dtype=float)

    slope = float(np.polyfit(x, sliced, 1)[0])

    return slope / mean_v


#     ================================
# --> Alpha
#     ================================

class AccumulationDistributionAlpha(PerSymbolAlpha):
    """A/D-vs-price slope divergence over a rolling window.

    Args:
        slope_window: Window for both slopes (default 20).
        hold_days: Informational ``close_time`` horizon.
    """

    name = "ad_divergence"
    required_columns = ("high", "low", "close", "volume")

    def __init__(
        self,
        slope_window: int = 20,
        hold_days: int = 10,
    ):
        self._window = slope_window
        self.hold_days = hold_days
        self.lookback = slope_window + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-(self._window + 1):]

        high = recent["high"]
        low = recent["low"]
        close = recent["close"]
        volume = recent["volume"]

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        ad = (clv * volume).cumsum()

        ad_slope = _normalized_slope(ad, self._window)
        price_slope = _normalized_slope(close, self._window)

        return ad_slope - price_slope

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized A/D-vs-price divergence.

        Implemented via rolling closed-form OLS slopes for both AD and
        price, normalized by rolling abs-mean so the spread is scale-
        free across tickers.
        """
        if panel.high is None or panel.low is None or panel.volume is None:
            raise ValueError(
                "AccumulationDistributionAlpha.compute_panel requires panel.high, "
                "panel.low, and panel.volume",
            )

        high = panel.high
        low = panel.low
        close = panel.close
        volume = panel.volume

        span = high - low

        clv = ((close - low) - (high - close)) / span.where(span > 0.0)
        clv = clv.fillna(0.0)

        ad = (clv * volume).cumsum()

        n = self._window
        x = np.arange(n, dtype=float)
        x_mean = x.mean()
        x_dev = x - x_mean
        x_var = float((x_dev ** 2).sum())

        def _slope(values: np.ndarray) -> float:
            return float((x_dev * (values - values.mean())).sum() / x_var)

        ad_slope_raw = ad.rolling(n).apply(_slope, raw=True)
        price_slope_raw = close.rolling(n).apply(_slope, raw=True)

        ad_norm = ad.abs().rolling(n).mean()
        price_norm = close.abs().rolling(n).mean()

        ad_slope = ad_slope_raw / ad_norm.where(ad_norm > 0.0)
        price_slope = price_slope_raw / price_norm.where(price_norm > 0.0)

        return ad_slope - price_slope
