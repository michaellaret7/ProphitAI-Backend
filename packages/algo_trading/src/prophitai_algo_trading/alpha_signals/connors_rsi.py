"""Connors RSI alpha — composite short-term mean-reversion oscillator.

Larry Connors (2012) combines three components into a single 0-100
oscillator that empirically captures short-horizon equity reversal
better than plain RSI:

    1. RSI(close, period_rsi)             — short-window momentum
    2. RSI(streak, period_streak)         — RSI of consecutive up/down
                                            day streak length, signed
    3. PercentRank(daily_return, period_rank)
                                          — where today's return ranks
                                            in the recent return distribution

    crsi  = (rsi_close + rsi_streak + pct_rank) / 3
    score = (50 - crsi) / 50

Distinct from plain RSI: Connors RSI explicitly weights *streak
persistence* and *recent return percentile* alongside oscillator —
historically tighter on equity index reversals (Connors documented
edge on SPY, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha
from prophitai_algo_trading.alpha_signals.helpers.streak import streak_series

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _rsi_series(values: "pd.Series", window: int) -> "pd.Series":
    """Wilder-style RSI as a series, returning 50 on flat windows."""
    diffs = values.diff()

    gains = diffs.where(diffs > 0.0, 0.0).rolling(window).mean()
    losses = (-diffs.where(diffs < 0.0, 0.0)).rolling(window).mean()

    total = gains + losses

    rsi = 100.0 * gains / total.where(total > 0.0)

    return rsi.fillna(50.0)


def _percent_rank_series(values: "pd.Series", window: int) -> "pd.Series":
    """Rolling percent-rank of the latest value against the prior window."""
    return values.rolling(window).rank(pct=True) * 100.0


#     ================================
# --> Alpha
#     ================================

class ConnorsRSIAlpha(PerSymbolAlpha):
    """Short-horizon composite RSI mean-reversion oscillator.

    Args:
        period_rsi: RSI window on close (default 3 — Connors's default).
        period_streak: RSI window on streak series (default 2).
        period_rank: Percent-rank window on daily returns (default 100).
        hold_days: Informational ``close_time`` horizon — Connors's
            published edge is over 2-5 days.
    """

    name = "connors_rsi"

    def __init__(
        self,
        period_rsi: int = 3,
        period_streak: int = 2,
        period_rank: int = 100,
        hold_days: int = 3,
    ):
        self._p_rsi = period_rsi
        self._p_streak = period_streak
        self._p_rank = period_rank
        self.hold_days = hold_days

        self.lookback = max(period_rsi, period_streak, period_rank) + 2

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        rsi_close = _rsi_series(closes, self._p_rsi)
        streak = streak_series(closes)
        rsi_streak = _rsi_series(streak, self._p_streak)
        returns = closes.pct_change()
        pct_rank = _percent_rank_series(returns, self._p_rank)

        rsi_c = float(rsi_close.iloc[-1])
        rsi_s = float(rsi_streak.iloc[-1])
        rank = float(pct_rank.iloc[-1])

        if any(v != v for v in (rsi_c, rsi_s, rank)):  # NaN check
            return None

        crsi = (rsi_c + rsi_s + rank) / 3.0

        return (50.0 - crsi) / 50.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized Connors RSI across the full panel.

        Each component is panel-wide: RSI on close, RSI on per-ticker
        signed streak, and rolling percent-rank of returns.
        """
        closes = panel.close

        streak = closes.apply(streak_series)

        rsi_close = _rsi_panel(closes, self._p_rsi)
        rsi_streak = _rsi_panel(streak, self._p_streak)

        returns = closes.pct_change()
        pct_rank = returns.rolling(self._p_rank).rank(pct=True) * 100.0

        crsi = (rsi_close + rsi_streak + pct_rank) / 3.0

        return (50.0 - crsi) / 50.0


#     ================================
# --> Panel-wide helper
#     ================================

def _rsi_panel(values: "pd.DataFrame", window: int) -> "pd.DataFrame":
    """Wilder-style RSI computed across an entire DataFrame at once."""
    diffs = values.diff()

    gains = diffs.where(diffs > 0.0, 0.0).rolling(window).mean()
    losses = (-diffs.where(diffs < 0.0, 0.0)).rolling(window).mean()

    total = gains + losses

    rsi = 100.0 * gains / total.where(total > 0.0)

    return rsi.fillna(50.0)
