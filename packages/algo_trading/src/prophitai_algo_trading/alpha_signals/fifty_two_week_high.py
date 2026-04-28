"""52-week-high proximity alpha.

George & Hwang (2004, J. Finance "The 52-Week High and Momentum
Investing") showed that a stock's distance from its 52-week high is a
robust momentum signal that captures behavioral *anchoring* — investors
treat the 52-week high as a salient reference point, and stocks
trading near it tend to continue outperforming.

    score = close / max(close over past 252 bars)

Score ∈ (0, 1]. Stocks at the 52-week high score 1.0; stocks far below
score near 0. Subtract the universe median post hoc to keep
cross-sectional balance, but the per-ticker raw score is already
useful as a long-only signal.

Distinct from 12-1 momentum: anchoring measures the *level* relative
to a recent peak, not the *return* over a window. Empirically
independent — the two together compound.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class FiftyTwoWeekHighAlpha(PerSymbolAlpha):
    """``close / 252-day max(close)`` — distance from the 52-week peak.

    Args:
        lookback_days: Window for the rolling max (default 252 bars =
            ~1 trading year).
        hold_days: Informational ``close_time`` horizon. The anchoring
            premium plays out over 1-6 months.
    """

    name = "fifty_two_week_high"

    def __init__(
        self,
        lookback_days: int = 252,
        hold_days: int = 21,
    ):
        self._window = lookback_days
        self.hold_days = hold_days
        self.lookback = lookback_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"].iloc[-self._window:]

        if len(closes) < self._window:
            return None

        peak = float(closes.max())

        if peak <= 0.0:
            return None

        current = float(closes.iloc[-1])

        if current <= 0.0:
            return None

        # Reason: subtract 0.5 to center the signal — roughly half the
        # universe sits in the upper-half of its 52w range, half in the
        # lower-half. Magnitude in [-0.5, +0.5].
        return current / peak - 0.5

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized 52-week-high proximity across the panel."""
        closes = panel.close

        rolling_max = closes.rolling(self._window).max()

        return closes / rolling_max.where(rolling_max > 0.0) - 0.5
