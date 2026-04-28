"""Stochastic %K oscillator alpha (mean-reversion).

Lane (1950s) Stochastic Oscillator measures where the close sits inside
the trailing N-bar range, normalized to 0-100:

    %K = 100 * (close - low_N) / (high_N - low_N)
    score = (50 - %K) / 50      ∈ [-1, +1]

Positive => close is in the lower half of the range (oversold → long).
Negative => close in the upper half (overbought → short).

Distinct from Donchian channel position: Stochastic is bounded [0, 100]
and Lane explicitly designed it for short-term mean-reversion, while
Donchian (which we already have) is typically used for breakout
trend-following. Same input, opposite use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class StochasticOscillatorAlpha(PerSymbolAlpha):
    """``(50 - %K) / 50`` mean-reversion score on the trailing range.

    Args:
        lookback_days: Window for high/low range (default 14 — Lane's
            standard).
        smooth_days: Optional smoothing of %K via a short SMA. Default
            3 (the classic %D smoothing).
        hold_days: Informational ``close_time`` horizon.
    """

    name = "stochastic"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        lookback_days: int = 14,
        smooth_days: int = 3,
        hold_days: int = 3,
    ):
        self._window = lookback_days
        self._smooth = smooth_days
        self.hold_days = hold_days

        self.lookback = lookback_days + smooth_days

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df.iloc[-(self._window + self._smooth):]

        high = recent["high"]
        low = recent["low"]
        close = recent["close"]

        # Reason: compute %K on the trailing window, smooth, then take last.
        rolling_high = high.rolling(self._window).max()
        rolling_low = low.rolling(self._window).min()

        span = rolling_high - rolling_low

        k_raw = 100.0 * (close - rolling_low) / span.where(span > 0.0)

        if self._smooth > 1:
            k_smooth = k_raw.rolling(self._smooth).mean()
        else:
            k_smooth = k_raw

        last = float(k_smooth.iloc[-1])

        if last != last:  # NaN check without imports
            return None

        return (50.0 - last) / 50.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized Stochastic %K mean-reversion across the panel."""
        if panel.high is None or panel.low is None:
            raise ValueError(
                "StochasticOscillatorAlpha.compute_panel requires panel.high "
                "and panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close

        rolling_high = high.rolling(self._window).max()
        rolling_low = low.rolling(self._window).min()

        span = rolling_high - rolling_low

        k_raw = 100.0 * (close - rolling_low) / span.where(span > 0.0)

        if self._smooth > 1:
            k_smooth = k_raw.rolling(self._smooth).mean()
        else:
            k_smooth = k_raw

        return (50.0 - k_smooth) / 50.0
