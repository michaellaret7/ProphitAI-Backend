"""Hourly Bollinger %B mean-reversion alpha.

Bollinger bands at 20-bar hourly cadence (~3 trading days). The %B
position normalizes the close to where it sits within the bands, then
mean-reverts on extremes:

    sma_20      = SMA(close, 20 bars)
    std_20      = std(close, 20 bars)
    upper       = sma_20 + 2 * std_20
    lower       = sma_20 - 2 * std_20
    pct_b       = (close - lower) / (upper - lower)        ∈ ~[0, 1]
    score       = 0.5 - pct_b

Positive score (close in lower half of band) ⇒ long candidate.
Negative ⇒ short. Distinct from RSI (oscillator on returns) — this
is a position-within-volatility-band measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class HourlyBollingerAlpha(PerSymbolAlpha):
    """``0.5 - %B`` mean-reversion on 20-bar hourly Bollinger bands."""

    name = "hourly_bollinger"

    def __init__(
        self,
        window: int = 20,
        n_std: float = 2.0,
        hold_days: int = 1,
    ):
        self._window = window
        self._n_std = n_std
        self.hold_days = hold_days
        self.lookback = window

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        recent = df["close"].iloc[-self._window:]

        if len(recent) < self._window:
            return None

        mean = float(recent.mean())
        std = float(recent.std(ddof=1))

        if std <= 0.0:
            return 0.0

        upper = mean + self._n_std * std
        lower = mean - self._n_std * std
        span = upper - lower

        if span <= 0.0:
            return 0.0

        cur = float(recent.iloc[-1])
        pct_b = (cur - lower) / span

        return 0.5 - pct_b

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        closes = panel.close

        sma = closes.rolling(self._window).mean()
        std = closes.rolling(self._window).std(ddof=1)

        upper = sma + self._n_std * std
        lower = sma - self._n_std * std
        span = upper - lower

        pct_b = (closes - lower) / span.where(span > 0.0)

        return (0.5 - pct_b).fillna(0.0)
