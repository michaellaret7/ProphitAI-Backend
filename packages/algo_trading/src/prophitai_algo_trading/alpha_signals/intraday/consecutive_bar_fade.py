"""Consecutive-bar fade alpha (intraday exhaustion reversal).

Streaks of N consecutive same-direction bars at hourly resolution
indicate persistent flow that frequently exhausts and reverses on the
next bar. The signal: count the current streak length (signed), and
emit a fade signal proportional to streak length once it exceeds a
threshold.

    streak_t = current consecutive same-direction bar count, signed
    score    = -streak_t / window     if |streak_t| >= threshold
               0                       otherwise

Streaks of 4+ same-direction bars are statistically rare; betting on
exhaustion captures a small but consistent edge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha
from prophitai_algo_trading.alpha_signals.helpers.streak import streak_series

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class ConsecutiveBarFadeAlpha(PerSymbolAlpha):
    """Fade after ``min_streak`` consecutive same-direction bars."""

    name = "consecutive_bar_fade"

    def __init__(
        self,
        min_streak: int = 4,
        normalize_window: int = 8,
        hold_days: int = 1,
    ):
        self._min = min_streak
        self._norm = normalize_window
        self.hold_days = hold_days

        self.lookback = max(min_streak, normalize_window) + 2

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        streak = streak_series(df["close"]).iloc[-1]

        if not np.isfinite(streak):
            return None

        if abs(streak) < self._min:
            return 0.0

        return -float(streak) / float(self._norm)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        streak_panel = panel.close.apply(streak_series)

        score = -streak_panel / float(self._norm)

        is_significant = streak_panel.abs() >= self._min

        return score.where(is_significant, 0.0).fillna(0.0)
