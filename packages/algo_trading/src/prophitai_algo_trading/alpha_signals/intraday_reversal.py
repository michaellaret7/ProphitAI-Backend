"""Intraday-reversal alpha — negate the same-day open-to-close return.

Heston, Korajczyk & Sadka (2010) and Bogousslavsky (2021, J. Finance)
showed that the intraday return component ``(close_t - open_t) /
open_t`` has a strong reversal pattern at the daily horizon — buying
yesterday's intraday losers and shorting yesterday's intraday winners
captures liquidity-provision premia.

    intraday_return = (close_t - open_t) / open_t
    score           = -intraday_return

Distinct from ``ShortTermReversalAlpha`` (which negates a multi-day
close-to-close return) and from ``GapFadeAlpha`` (which negates the
overnight gap). The three together fully decompose the recent return
into orthogonal "fade these extreme moves" signals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class IntradayReversalAlpha(PerSymbolAlpha):
    """Negated intraday (open → close) return.

    Args:
        smoothing_days: Optional rolling-mean window over the negated
            intraday return — useful to dampen single-day noise.
            Default 1 (no smoothing — pure same-day signal).
        hold_days: Informational ``close_time`` horizon. Intraday
            reversal plays out over 1-2 sessions.
    """

    name = "intraday_reversal"
    required_columns = ("open", "close")

    def __init__(
        self,
        smoothing_days: int = 1,
        hold_days: int = 2,
    ):
        if smoothing_days < 1:
            raise ValueError(
                f"smoothing_days must be >= 1, got {smoothing_days}",
            )

        self._smooth = smoothing_days
        self.hold_days = hold_days

        # Reason: need at least the smoothing window's worth of bars.
        self.lookback = smoothing_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-self._smooth:]

        opens = recent["open"]
        closes = recent["close"]

        if (opens <= 0.0).any():
            return None

        intraday = (closes - opens) / opens

        if intraday.isna().any():
            return None

        return -float(intraday.mean())

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized negated intraday return across the panel."""
        if panel.open is None:
            raise ValueError(
                "IntradayReversalAlpha.compute_panel requires panel.open",
            )

        opens = panel.open
        closes = panel.close

        intraday = (closes - opens) / opens.where(opens > 0.0)

        if self._smooth > 1:
            intraday = intraday.rolling(self._smooth).mean()

        return -intraday
