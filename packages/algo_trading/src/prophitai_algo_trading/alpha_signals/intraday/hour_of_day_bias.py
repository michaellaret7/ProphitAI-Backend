"""Hour-of-day historical bias alpha (intraday).

Each hour of the trading day has a distinct empirical return pattern
across US equities — driven by opening-auction overshoot, mid-day
liquidity gaps, and closing-auction flow. This alpha computes the
historical mean return for *this hour-of-day* and emits it as a score.

    for each (ticker, hour_of_day):
        mean_return_at_hour = mean(close/close[-1] - 1) restricted to that hour

    score = mean_return_at_hour      (slow-decay seasonal)

Distinct from a calendar-day signal: this is the *hour pattern*
within each session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


class HourOfDayBiasAlpha(PerSymbolAlpha):
    """Per-ticker, per-hour-of-day historical mean return.

    Args:
        history_bars: Window over which the per-hour mean is estimated
            (default 250 ≈ ~5 weeks of trading hours).
        hold_days: ``close_time`` horizon (default 1).
    """

    name = "hour_of_day_bias"

    def __init__(
        self,
        history_bars: int = 250,
        hold_days: int = 1,
    ):
        self._history = history_bars
        self.hold_days = hold_days
        self.lookback = history_bars + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        timestamp = df.index[-1]

        if not isinstance(timestamp, pd.Timestamp):
            timestamp = pd.Timestamp(timestamp)

        recent = df.iloc[-self._history:]
        recent_returns = recent["close"].pct_change().dropna()

        if len(recent_returns) < 20:
            return None

        # Match bars to their hour, then take the mean for the current hour.
        hours = pd.Series(recent_returns.index.hour, index=recent_returns.index)
        same_hour_returns = recent_returns[hours == timestamp.hour]

        if len(same_hour_returns) < 5:
            return None

        mean_return = float(same_hour_returns.mean())

        if not np.isfinite(mean_return):
            return None

        return mean_return

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized: per (date, ticker) emit the rolling-history mean
        return for that bar's hour-of-day.

        Implemented per-ticker via groupby on hour, expanding mean
        within each hour group, then re-aligned to the original index.
        """
        returns = panel.close.pct_change()

        hour_series = pd.Series(panel.index.hour, index=panel.index)

        # For each column, compute hour-grouped expanding mean over the
        # rolling window. Vectorized via groupby + transform with a
        # rolling mean.
        result_cols: dict[str, pd.Series] = {}

        for ticker in panel.tickers:
            ret_col = returns[ticker]

            # Reason: rolling mean restricted to same hour-of-day. Group
            # by hour, take rolling mean within each group, then re-align.
            grouped = ret_col.groupby(hour_series)
            rolling_means = grouped.transform(
                lambda s: s.rolling(self._history // 7, min_periods=3).mean()
            )
            result_cols[ticker] = rolling_means

        return pd.DataFrame(result_cols, index=panel.index).fillna(0.0)
