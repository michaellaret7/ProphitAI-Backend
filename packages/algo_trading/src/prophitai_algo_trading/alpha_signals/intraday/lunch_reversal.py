"""Lunch-hour mean-reversion alpha (intraday).

US equity volume forms a U-shape across the session — heavy at the
open, thin at lunch, heavy at the close. The lunch hour (~17 UTC =
12-1pm ET) is dominated by retail and small-order flow rather than
institutional, and short-horizon moves there tend to mean-revert as
the afternoon institutional flow restores prices.

The signal fires only on lunch-hour bars; on non-lunch hours it emits
zero. On lunch bars, the score is the negated 3-bar return.

    lunch_hours_utc = {16, 17, 18}        # ~11am-2pm ET
    score = -((close - close[t-3]) / close[t-3])  if hour ∈ lunch_hours
            0                                       otherwise
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


_LUNCH_HOURS_UTC = (16, 17, 18)


class LunchReversalAlpha(PerSymbolAlpha):
    """Negated 3-bar return, fires only on lunch-hour bars.

    Args:
        return_window: Number of bars over which the return-to-fade is
            measured (default 3).
        hold_days: ``close_time`` horizon (default 1).
    """

    name = "lunch_reversal"

    def __init__(
        self,
        return_window: int = 3,
        hold_days: int = 1,
    ):
        self._window = return_window
        self.hold_days = hold_days

        self.lookback = return_window + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        if timestamp.hour not in _LUNCH_HOURS_UTC:
            return 0.0

        closes = df["close"]

        start_price = float(closes.iloc[-(self._window + 1)])
        current = float(closes.iloc[-1])

        if start_price <= 0.0 or current <= 0.0:
            return None

        return -((current / start_price) - 1.0)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized lunch-hour reversal across the panel.

        Compute the panel-wide N-bar return, negate, then mask to zero
        on non-lunch-hour bars.
        """
        ret = -panel.close.pct_change(self._window)

        hours = pd.Series(panel.index.hour, index=panel.index)
        is_lunch = hours.isin(_LUNCH_HOURS_UTC)

        mask = pd.DataFrame(
            is_lunch.to_numpy().reshape(-1, 1).repeat(len(panel.tickers), axis=1),
            index=panel.index,
            columns=panel.tickers,
        )

        return ret.where(mask, 0.0)
