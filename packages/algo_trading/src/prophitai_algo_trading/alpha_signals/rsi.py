"""RSI mean-reversion alpha.

Wilder-style Relative Strength Index over a daily-close window. RSI
compresses N bars of gains/losses into a 0-100 oscillator; the crowded
extremes (oversold near 0, overbought near 100) tend to mean-revert
short-term.

    rs    = mean(gains_N) / mean(losses_N)
    rsi   = 100 - 100 / (1 + rs)
    score = (50 - rsi) / 50              # range [-1, +1]

Positive score => oversold (long candidate). Negative => overbought
(short candidate). The signal is orthogonal to raw 5-day reversal
because RSI smooths the up/down moves separately rather than netting
them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class RSIAlpha(PerSymbolAlpha):
    """RSI-based mean-reversion score in ``[-1, +1]``.

    Args:
        lookback_days: RSI window (default 14 — Wilder's original).
        hold_days: Informational ``close_time`` horizon. RSI mean-
            reversion plays out over a few days.
    """

    name = "rsi"

    def __init__(
        self,
        lookback_days: int = 14,
        hold_days: int = 3,
    ):
        self._window = lookback_days
        self.hold_days = hold_days

        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        diffs = closes.iloc[-(self._window + 1):].diff().dropna()

        if len(diffs) < self._window:
            return None

        gains = float(diffs.clip(lower=0.0).mean())
        losses = float((-diffs.clip(upper=0.0)).mean())

        total = gains + losses

        if total <= 0.0:
            rsi = 50.0
        else:
            rsi = 100.0 * gains / total

        return (50.0 - rsi) / 50.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized RSI score across the full ``[date x ticker]`` panel.

        ``RSI = 100 * gains / (gains + losses)`` — algebraically
        equivalent to ``100 - 100 / (1 + gains/losses)`` but avoids the
        div-by-zero when the loss window is all zeros. Flat windows
        (``gains + losses == 0``) default to ``rsi = 50`` (neutral).
        """
        diffs = panel.close.diff()

        gains = diffs.clip(lower=0.0).rolling(self._window).mean()
        losses = (-diffs.clip(upper=0.0)).rolling(self._window).mean()

        total = gains + losses

        rsi = 100.0 * gains / total.where(total > 0.0)
        rsi = rsi.fillna(50.0)

        return (50.0 - rsi) / 50.0
