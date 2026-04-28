"""Close-of-session drift alpha (intraday).

The last hour of US trading frequently sees institutional MOC (market-
on-close) flow plus index-rebalancing trades from passive funds.
Stocks that have led the day's accumulation tend to keep drifting in
the same direction into the close. The signal: on close-hour bars,
score equals the day's cumulative return so far.

    close_hours_utc = {19, 20}             # ~2-4pm ET
    score = (close[t] - open_today) / open_today   on close-hour bars
            0                                       otherwise

Distinct from a multi-bar momentum signal: the lookback resets at
each session open, so we capture *intraday* persistence specifically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


_CLOSE_HOURS_UTC = (19, 20)


class CloseDriftAlpha(PerSymbolAlpha):
    """Day's cumulative return so far, fires only on close-hour bars."""

    name = "close_drift"
    required_columns = ("open", "close")

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days
        self.lookback = 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        if timestamp.hour not in _CLOSE_HOURS_UTC:
            return 0.0

        today_bars = df[df.index.normalize() == timestamp.normalize()]

        if today_bars.empty:
            return None

        day_open = float(today_bars["open"].iloc[0])
        current = float(df["close"].iloc[-1])

        if day_open <= 0.0 or current <= 0.0:
            return None

        return (current / day_open) - 1.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized: per (date, ticker) emit the day's cumulative return on
        close-hour bars only.
        """
        if panel.open is None:
            raise ValueError(
                "CloseDriftAlpha.compute_panel requires panel.open",
            )

        opens = panel.open
        closes = panel.close

        date_index = pd.Series(panel.index.normalize(), index=panel.index)

        # First open of each day, broadcast across the day's bars
        day_open = opens.groupby(date_index).transform("first")

        cumulative_return = (closes / day_open.where(day_open > 0.0)) - 1.0

        hours = pd.Series(panel.index.hour, index=panel.index)
        is_close_hour = hours.isin(_CLOSE_HOURS_UTC)

        mask = pd.DataFrame(
            is_close_hour.to_numpy().reshape(-1, 1).repeat(len(panel.tickers), axis=1),
            index=panel.index,
            columns=panel.tickers,
        )

        return cumulative_return.where(mask, 0.0)
