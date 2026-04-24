"""ATR-normalized momentum alpha.

20-day price return divided by ATR-percent:

    atr       = mean over 14 bars of max(high-low, |high-prev_close|, |low-prev_close|)
    atr_pct   = atr / close_today
    ret       = close_today / close_20d_ago - 1
    score     = ret / atr_pct

Volatility-adjusted momentum — a quiet 5% move scores higher than a
noisy 5% move, because the former is more likely a stable trend and
the latter is more likely random chop. Lets the PCM size positions by
signal quality rather than raw price change.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.alphas.base import PerSymbolAlpha


class ATRNormalizedMomentumAlpha(PerSymbolAlpha):
    """Return-over-ATR momentum.

    Args:
        return_window: Bars for the return numerator (default 20).
        atr_window: Bars for the ATR denominator (default 14 — Wilder).
        hold_days: Insight close_time horizon.
    """

    name = "atr_momentum"

    def __init__(
        self,
        return_window: int = 20,
        atr_window: int = 14,
        hold_days: int = 5,
    ):
        self._return_window = return_window
        self._atr_window = atr_window
        self.hold_days = hold_days

        # Reason: return_window+1 closes for the return numerator;
        # atr_window+1 bars for the true-range with prev_close.
        self.lookback = max(return_window + 1, atr_window + 1)

    def compute_score(self, df: pd.DataFrame) -> float | None:
        closes = df["close"]
        highs = df["high"]
        lows = df["low"]

        start = float(closes.iloc[-(self._return_window + 1)])
        end = float(closes.iloc[-1])

        if start <= 0.0 or end <= 0.0:
            return None

        recent_return = (end / start) - 1.0

        prev_close = closes.shift(1).iloc[-self._atr_window:]
        high_window = highs.iloc[-self._atr_window:]
        low_window = lows.iloc[-self._atr_window:]

        true_range = pd.concat([
            high_window - low_window,
            (high_window - prev_close).abs(),
            (low_window - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr = float(true_range.mean())

        if atr <= 0.0 or not np.isfinite(atr):
            return None

        atr_pct = atr / end

        if atr_pct <= 0.0:
            return None

        return recent_return / atr_pct
