"""Momentum acceleration alpha — change of trend, not level of trend.

Compares two consecutive return windows:

    ret_recent = close[t]      / close[t - W]      - 1
    ret_prior  = close[t - W]  / close[t - 2W]     - 1
    score      = ret_recent - ret_prior

Positive => trend is *speeding up* (accelerating uptrend or decelerating
downtrend → mean reversion bid). Negative => trend is *losing steam*
(decelerating uptrend or accelerating downdraft).

Orthogonal to plain 12-1 momentum because acceleration measures the
*second derivative* of price — a trend can be strong (high momentum)
but flat (zero acceleration) or weak (low momentum) but accelerating
(positive jolt).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class AccelerationAlpha(PerSymbolAlpha):
    """Difference of consecutive equal-length return windows.

    Args:
        window_days: Length of each return window (default 21 = ~one
            trading month). The lookback covers two consecutive windows.
        hold_days: Informational ``close_time`` horizon. Acceleration
            decays faster than steady momentum.
    """

    name = "acceleration"

    def __init__(
        self,
        window_days: int = 21,
        hold_days: int = 5,
    ):
        self._window = window_days
        self.hold_days = hold_days

        # Reason: need 2W + 1 closes so close[t - 2W] exists.
        self.lookback = 2 * window_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        price_now = float(closes.iloc[-1])
        price_mid = float(closes.iloc[-(self._window + 1)])
        price_old = float(closes.iloc[-(2 * self._window + 1)])

        if price_old <= 0.0 or price_mid <= 0.0:
            return None

        ret_recent = price_now / price_mid - 1.0
        ret_prior = price_mid / price_old - 1.0

        return ret_recent - ret_prior

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized acceleration across the full panel.

        ``pct_change(W) - pct_change(W).shift(W)`` — the W-bar return
        minus the W-bar return ending W bars ago.
        """
        ret = panel.close.pct_change(self._window)

        return ret - ret.shift(self._window)
