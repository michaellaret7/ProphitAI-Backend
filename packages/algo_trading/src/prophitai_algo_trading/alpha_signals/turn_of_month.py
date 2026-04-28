"""Turn-of-Month seasonality alpha.

Ariel (1987, JFE) and Lakonishok & Smidt (1988, RFS) documented that
US equity returns concentrate around the turn of the calendar month —
the last trading day plus the first three trading days of the next
month earn statistically significant excess returns. The effect has
persisted post-publication, reportedly driven by 401(k) / pension
inflows clustering near month-end.

The alpha emits +1 on the last bar of one month and the first three
bars of the next, zero everywhere else. Magnitude scaled by the
historical mean monthly return for that ticker so different volatility
regimes don't dominate the cross-section:

    score = is_tom_window * mean_return_per_bar(ticker, lookback)

Pure calendar effect — orthogonal axis to every price-based alpha.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _is_tom_bar(index: pd.DatetimeIndex) -> pd.Series:
    """Boolean series — True on the last trading day of a month and the
    first three trading days of the next month.

    Implemented by checking the *next* business day's month change for
    "last day of month" and counting forward business days from that
    boundary for "first three of next month."
    """
    # Reason: the cleanest detector is to check if the bar's calendar
    # month differs from the next bar's month — then the bar is the
    # last trading day. From that boundary the next 3 bars are TOM.
    next_month = pd.Series(index.to_series().dt.month.shift(-1), index=index)
    is_last = (index.to_series().dt.month != next_month) & next_month.notna()

    # First three bars of the next month: the bar just after the last
    # of the previous month, and the next two.
    is_tom = pd.Series(False, index=index)

    is_tom = is_tom | is_last

    is_tom = is_tom | is_last.shift(1, fill_value=False)
    is_tom = is_tom | is_last.shift(2, fill_value=False)
    is_tom = is_tom | is_last.shift(3, fill_value=False)

    return is_tom


#     ================================
# --> Alpha
#     ================================

class TurnOfMonthAlpha(PerSymbolAlpha):
    """+1 on TOM-window bars (scaled by per-ticker historical mean), 0 else.

    Args:
        history_days: Window over which the per-ticker mean return is
            estimated (default 252 = ~1 year).
        hold_days: Informational ``close_time`` horizon — TOM-window
            spans 4 trading days.
    """

    name = "turn_of_month"

    def __init__(
        self,
        history_days: int = 252,
        hold_days: int = 4,
    ):
        self._history = history_days
        self.hold_days = hold_days

        self.lookback = history_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        # Reason: the 'now' bar is df.iloc[-1]; check whether it sits in
        # the TOM window by looking at next-bar month vs current month.
        # Because the per-bar engine has no "next bar," we approximate:
        # check if today is in the last-3 or first-3 calendar-day band.
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        day = timestamp.day

        days_in_month = (timestamp + pd.offsets.MonthEnd(0)).day

        in_tom = (days_in_month - day) <= 1 or day <= 3

        if not in_tom:
            return 0.0

        returns = df["close"].pct_change().iloc[-self._history:].dropna()

        if len(returns) < max(20, self._history // 4):
            return None

        mean_return = float(returns.mean())

        if not np.isfinite(mean_return):
            return None

        return abs(mean_return) if mean_return >= 0.0 else mean_return

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized TOM mask × per-ticker mean return.

        Each TOM-window bar emits the ticker's rolling-mean daily return;
        non-TOM bars emit zero.
        """
        is_tom = _is_tom_bar(panel.index)

        returns = panel.close.pct_change()

        mean_return = returns.rolling(self._history).mean()

        # Reason: shape an indicator panel matching the close panel by
        # broadcasting the bar-mask across columns.
        mask = pd.DataFrame(
            np.broadcast_to(
                is_tom.to_numpy().reshape(-1, 1),
                (len(panel.index), len(panel.tickers)),
            ),
            index=panel.index,
            columns=panel.tickers,
        )

        return mean_return.where(mask, 0.0)
