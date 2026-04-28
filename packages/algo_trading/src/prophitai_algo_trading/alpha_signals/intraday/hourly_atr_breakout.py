"""Hourly ATR breakout alpha (vol-scaled momentum).

A hourly bar that prints with above-average true range AND closes in
the same direction as the move is a high-conviction directional bar.
Vol-scaling the move so cross-sectional comparisons are fair:

    tr_t        = max(H-L, |H - prev_close|, |L - prev_close|)
    atr         = mean(tr over past N bars)
    move_t      = close[t] - close[t-1]
    score       = move / atr           (signed, naturally vol-scaled)

Score is in standard-deviation-like units. Distinct from raw return:
small absolute moves on tight ATR get amplified, large moves on wide
ATR get dampened — captures *significance*, not just magnitude.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class HourlyATRBreakoutAlpha(PerSymbolAlpha):
    """Vol-normalized one-bar move via ATR scaling."""

    name = "hourly_atr_breakout"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        atr_window: int = 20,
        hold_days: int = 1,
    ):
        self._atr_window = atr_window
        self.hold_days = hold_days
        self.lookback = atr_window + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-(self._atr_window + 1):]

        high = recent["high"]
        low = recent["low"]
        close = recent["close"]
        prev_close = close.shift(1)

        range_hl = high - low
        range_hc = (high - prev_close).abs()
        range_lc = (low - prev_close).abs()

        tr = np.maximum(np.maximum(range_hl, range_hc), range_lc)

        atr = float(tr.iloc[-self._atr_window:].mean())

        if atr <= 0.0:
            return None

        prev_c = float(close.iloc[-2])
        cur_c = float(close.iloc[-1])

        return (cur_c - prev_c) / atr

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        if panel.high is None or panel.low is None:
            raise ValueError(
                "HourlyATRBreakoutAlpha.compute_panel requires panel.high and "
                "panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close

        prev_close = close.shift(1)

        range_hl = high - low
        range_hc = (high - prev_close).abs()
        range_lc = (low - prev_close).abs()

        tr = np.maximum(np.maximum(range_hl, range_hc), range_lc)

        atr = tr.rolling(self._atr_window).mean()

        move = close.diff()

        return move / atr.where(atr > 0.0)
