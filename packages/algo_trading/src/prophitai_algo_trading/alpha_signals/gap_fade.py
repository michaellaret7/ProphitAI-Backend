"""Overnight-gap fade alpha.

Stocks that gap sharply at the open often fail to hold the move and
"fill the gap" intraday. Score the rolling sum of recent overnight gaps
and negate so big up-gaps become short signals (and big down-gaps long).

    gap_pct   = open[t] / close[t-1] - 1
    score     = -mean(gap_pct over last N days)

The averaging smooths over single-bar noise; persistent up-gaps over
several days build a stronger fade signal than a one-off opening pop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class GapFadeAlpha(PerSymbolAlpha):
    """Negated rolling mean of overnight ``open / prev_close`` gaps.

    Args:
        lookback_days: Number of recent gaps to average (default 3).
        hold_days: Informational ``close_time`` horizon. Gap fills play
            out within a few sessions, so keep this short.
    """

    name = "gap_fade"
    required_columns = ("open", "close")

    def __init__(
        self,
        lookback_days: int = 3,
        hold_days: int = 2,
    ):
        self._window = lookback_days
        self.hold_days = hold_days

        # Reason: need lookback+1 closes so the first gap has a prev_close.
        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        opens = df["open"].iloc[-self._window:]
        prev_closes = df["close"].shift(1).iloc[-self._window:]

        if prev_closes.isna().any() or (prev_closes <= 0.0).any():
            return None

        gaps = (opens / prev_closes) - 1.0

        if gaps.isna().any():
            return None

        return -float(gaps.mean())

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized gap-fade score across the full panel.

        Per-bar overnight gap = ``open / close.shift(1) - 1``; rolling
        mean over the lookback, then negated.
        """
        if panel.open is None:
            raise ValueError(
                "GapFadeAlpha.compute_panel requires panel.open",
            )

        prev_close = panel.close.shift(1)

        gap = (panel.open / prev_close.where(prev_close > 0.0)) - 1.0

        return -gap.rolling(self._window).mean()
