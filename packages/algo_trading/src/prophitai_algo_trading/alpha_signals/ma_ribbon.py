"""Moving-average ribbon alpha — fast vs slow SMA spread, normalized.

Distance between a fast and a slow simple moving average, scaled by the
current close. Captures *trend regime* in a way that's complementary to
12-1 momentum: 12-1 is a single-window return, the ribbon is the
*difference of two smoothed paths*, which is more robust to single-day
shocks at either end of the window.

    score = (sma_fast - sma_slow) / close

Positive => fast above slow => uptrend regime (long candidate).
Negative => downtrend regime (short candidate).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class MovingAverageRibbonAlpha(PerSymbolAlpha):
    """Normalized fast-vs-slow SMA spread.

    Args:
        fast_days: Fast SMA window (default 20 = ~one trading month).
        slow_days: Slow SMA window (default 50 = ~one quarter).
        hold_days: Informational ``close_time`` horizon. Ribbon regimes
            persist for weeks, so hold longer than breakout/reversal.
    """

    name = "ma_ribbon"

    def __init__(
        self,
        fast_days: int = 20,
        slow_days: int = 50,
        hold_days: int = 10,
    ):
        if fast_days >= slow_days:
            raise ValueError(
                f"fast_days ({fast_days}) must be < slow_days ({slow_days})",
            )

        self._fast = fast_days
        self._slow = slow_days
        self.hold_days = hold_days

        self.lookback = slow_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        sma_fast = float(closes.iloc[-self._fast:].mean())
        sma_slow = float(closes.iloc[-self._slow:].mean())

        current = float(closes.iloc[-1])

        if current <= 0.0:
            return None

        return (sma_fast - sma_slow) / current

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized SMA-ribbon spread across the full panel.

        ``(rolling_mean(fast) - rolling_mean(slow)) / close``
        """
        closes = panel.close

        sma_fast = closes.rolling(self._fast).mean()
        sma_slow = closes.rolling(self._slow).mean()

        spread = sma_fast - sma_slow

        return spread.div(closes.where(closes > 0.0))
