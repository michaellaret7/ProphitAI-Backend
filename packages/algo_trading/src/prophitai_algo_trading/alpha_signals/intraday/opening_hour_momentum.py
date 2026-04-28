"""Opening-hour momentum alpha (intraday).

The first hour of US equity trading is the most informative bar of the
day — the overnight news has been priced in, large institutions
execute opening orders, and the resulting direction tends to persist
through mid-day. The signal: sign and magnitude of today's *first*
hourly bar's return, only fires on bars that fall in the same trading
day as that opening bar.

    open_bar = first bar of today's session
    score    = (close - open) / open of that bar, persists for the day

Score decays to zero at the start of the next session — the alpha is
explicitly an intraday persistence trade.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


class OpeningHourMomentumAlpha(PerSymbolAlpha):
    """Today's first-bar return — persists through the rest of the session.

    Args:
        hold_days: ``close_time`` horizon (default 1 = next-day close).
            Internally the signal is intraday: it zeros out on the next
            session's first bar.
    """

    name = "opening_hour_momentum"
    required_columns = ("open", "close")

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days

        # Reason: only need today's first bar, but require ≥1 bar to compute.
        self.lookback = 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        today = timestamp.normalize()

        today_bars = df[df.index.normalize() == today]

        if today_bars.empty:
            return None

        first_open = float(today_bars["open"].iloc[0])
        first_close = float(today_bars["close"].iloc[0])

        if first_open <= 0.0:
            return None

        return (first_close / first_open) - 1.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized: per (date, ticker) emit today's first-bar return.

        Built by groupby on the date component, taking the first bar's
        ``close/open - 1``, then broadcasting that scalar across every
        bar of the same day.
        """
        if panel.open is None:
            raise ValueError(
                "OpeningHourMomentumAlpha.compute_panel requires panel.open",
            )

        opens = panel.open
        closes = panel.close

        first_bar_return = (closes / opens.where(opens > 0.0)) - 1.0

        date_index = pd.Series(panel.index.normalize(), index=panel.index)
        first_bar_per_day = first_bar_return.groupby(date_index).transform("first")

        return first_bar_per_day
