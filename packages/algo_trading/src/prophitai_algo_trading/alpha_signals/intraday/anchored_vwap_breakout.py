"""Anchored-VWAP breakout alpha (intraday momentum).

Anchored VWAP starts from the day's first bar and accumulates
volume-weighted price through the session. When price *breaks* above
the anchored VWAP after trading below it (or vice versa), institutions
defending VWAP execution often add to the new direction. The signal:

    cross_up   = close > vwap & prev_close <= prev_vwap
    cross_down = close < vwap & prev_close >= prev_vwap
    score      = +distance_from_vwap   if cross_up
                 -distance_from_vwap   if cross_down
                 0                     otherwise

Distinct from ``SessionVWAPDeviationAlpha`` which always emits a
mean-reversion bias proportional to deviation. This alpha fires only
on *fresh* crosses — momentum, not reversion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


class AnchoredVWAPBreakoutAlpha(PerSymbolAlpha):
    """Day-anchored VWAP cross-over momentum signal."""

    name = "anchored_vwap_breakout"
    required_columns = ("high", "low", "close", "volume")

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days
        self.lookback = 2

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        today_bars = df[df.index.normalize() == timestamp.normalize()]

        if len(today_bars) < 2:
            return 0.0

        typical = (today_bars["high"] + today_bars["low"] + today_bars["close"]) / 3.0
        volume = today_bars["volume"]

        cum_pv = (typical * volume).cumsum()
        cum_vol = volume.cumsum()

        vwap = cum_pv / cum_vol.where(cum_vol > 0.0)

        close = today_bars["close"]

        prev_close = float(close.iloc[-2])
        prev_vwap = float(vwap.iloc[-2])
        cur_close = float(close.iloc[-1])
        cur_vwap = float(vwap.iloc[-1])

        if cur_vwap <= 0.0:
            return None

        deviation = (cur_close / cur_vwap) - 1.0

        cross_up = cur_close > cur_vwap and prev_close <= prev_vwap
        cross_down = cur_close < cur_vwap and prev_close >= prev_vwap

        if cross_up:
            return abs(deviation)

        if cross_down:
            return -abs(deviation)

        return 0.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized anchored VWAP breakout signal across the panel."""
        if panel.high is None or panel.low is None or panel.volume is None:
            raise ValueError(
                "AnchoredVWAPBreakoutAlpha.compute_panel requires high/low/volume",
            )

        typical = (panel.high + panel.low + panel.close) / 3.0
        volume = panel.volume

        date_index = pd.Series(panel.index.normalize(), index=panel.index)

        cum_pv = (typical * volume).groupby(date_index).cumsum()
        cum_vol = volume.groupby(date_index).cumsum()

        vwap = cum_pv / cum_vol.where(cum_vol > 0.0)

        close = panel.close

        is_above = close > vwap
        prev_above = is_above.shift(1)

        # Fresh cross: position changed since previous bar
        cross_up = is_above & ~prev_above.fillna(False)
        cross_down = ~is_above & prev_above.fillna(False)

        deviation = (close / vwap.where(vwap > 0.0)) - 1.0

        score = pd.DataFrame(
            np.where(cross_up, deviation.abs(), 0.0),
            index=panel.index,
            columns=panel.tickers,
        )
        score = score.where(~cross_down, -deviation.abs())

        return score.fillna(0.0)
