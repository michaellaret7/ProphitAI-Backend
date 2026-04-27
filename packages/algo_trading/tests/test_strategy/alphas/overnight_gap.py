"""Overnight-gap persistence alpha.

Overnight returns (close -> next open) have a documented non-zero drift
distinct from intraday returns. This alpha measures a ticker's recent
average overnight return and bets on its continuation:

    overnight_ret_t = open_t / close_{t-1} - 1
    score           = mean(overnight_ret_t) over lookback window

Positive average overnight drift -> long bias. Negative -> short.
Magnitude is the raw mean overnight return, so strong persistent gap
behavior emits higher signal than noisy mixed gaps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha


class OvernightGapAlpha(PerSymbolAlpha):
    """Rolling mean of overnight returns — gap-persistence signal.

    Args:
        lookback_days: Window over which overnight returns are averaged.
        hold_days: Insight close_time horizon.
    """

    name = "overnight_gap"
    required_columns = ("open", "close")

    def __init__(self, lookback_days: int = 20, hold_days: int = 3):
        self._window = lookback_days
        self.hold_days = hold_days

        # Reason: need window+1 bars so the prev-close shift has data.
        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        opens = df["open"]
        closes = df["close"]

        prev_close = closes.shift(1)

        overnight = (opens / prev_close - 1.0).iloc[-self._window:]
        overnight = overnight.dropna()

        if len(overnight) < self._window // 2:
            return None

        mean_gap = float(overnight.mean())

        if not np.isfinite(mean_gap):
            return None

        return mean_gap
