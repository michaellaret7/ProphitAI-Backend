"""Hourly RSI mean-reversion alpha.

14-bar RSI on hourly closes ≈ 2 trading days of price action,
recalibrated for intraday horizons. Same form as the daily ``RSIAlpha``
but at the hourly granularity:

    rsi   = 100 * gains / (gains + losses)   over past 14 bars
    score = (50 - rsi) / 50

Positive => oversold (long candidate); negative => overbought.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class HourlyRSIAlpha(PerSymbolAlpha):
    """14-bar RSI mean-reversion on hourly closes."""

    name = "hourly_rsi"

    def __init__(
        self,
        lookback_bars: int = 14,
        hold_days: int = 1,
    ):
        self._window = lookback_bars
        self.hold_days = hold_days
        self.lookback = lookback_bars + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        diffs = df["close"].iloc[-(self._window + 1):].diff().dropna()

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
        diffs = panel.close.diff()

        gains = diffs.clip(lower=0.0).rolling(self._window).mean()
        losses = (-diffs.clip(upper=0.0)).rolling(self._window).mean()

        total = gains + losses

        rsi = 100.0 * gains / total.where(total > 0.0)
        rsi = rsi.fillna(50.0)

        return (50.0 - rsi) / 50.0
