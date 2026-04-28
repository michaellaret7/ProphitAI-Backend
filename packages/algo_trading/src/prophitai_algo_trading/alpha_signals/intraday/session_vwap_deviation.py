"""Session-VWAP deviation alpha (intraday mean-reversion).

VWAP (volume-weighted average price) is the auction-fair benchmark of
the day. Institutional traders frequently target VWAP execution; when
price deviates significantly above or below VWAP intraday, mean-
reversion flow tends to drag it back. The signal: negate the deviation
of the current close from session-VWAP.

    typical_t   = (high + low + close) / 3
    cumvol_t    = cumulative volume since session open
    vwap_t      = sum(typical * volume) / cumvol  (anchored at day open)
    score       = -((close - vwap) / vwap)

Negative deviation (close < vwap) gets a positive score (long candidate
expecting mean revert up). Positive deviation gets negative (short).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


class SessionVWAPDeviationAlpha(PerSymbolAlpha):
    """Negated (close - vwap) / vwap, anchored at session open."""

    name = "vwap_deviation"
    required_columns = ("high", "low", "close", "volume")

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days
        self.lookback = 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        today_bars = df[df.index.normalize() == timestamp.normalize()]

        if today_bars.empty:
            return None

        typical = (today_bars["high"] + today_bars["low"] + today_bars["close"]) / 3.0
        volume = today_bars["volume"]

        cum_vol = float(volume.sum())

        if cum_vol <= 0.0:
            return None

        vwap = float((typical * volume).sum()) / cum_vol

        current = float(today_bars["close"].iloc[-1])

        if vwap <= 0.0 or current <= 0.0:
            return None

        return -((current / vwap) - 1.0)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized: anchored session VWAP per ticker, deviation negated."""
        if panel.high is None or panel.low is None or panel.volume is None:
            raise ValueError(
                "SessionVWAPDeviationAlpha.compute_panel requires high/low/volume",
            )

        typical = (panel.high + panel.low + panel.close) / 3.0
        volume = panel.volume

        date_index = pd.Series(panel.index.normalize(), index=panel.index)

        cum_pv = (typical * volume).groupby(date_index).cumsum()
        cum_vol = volume.groupby(date_index).cumsum()

        vwap = cum_pv / cum_vol.where(cum_vol > 0.0)

        deviation = (panel.close / vwap.where(vwap > 0.0)) - 1.0

        return -deviation.fillna(0.0)
