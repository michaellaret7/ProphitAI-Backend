"""MACD histogram trend-following alpha.

Pure MACD histogram — a classical trend-following signal. The
histogram (MACD line minus its signal line) prints positive during
strengthening uptrends and negative during strengthening downtrends.

    macd_line   = EMA(close, fast) - EMA(close, slow)
    signal_line = EMA(macd_line, signal)
    hist        = macd_line - signal_line

    score       = hist / price_today    # normalize by price so the
                                        # raw dollar units don't make
                                        # high-priced stocks dominate

Positive histogram = long, negative = short. Distinct from
``ATRNormalizedMomentumAlpha`` because MACD picks up shorter-horizon
trend strength from EMA crossovers, while ATR momentum measures raw
multi-week return. Including both adds information.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.alphas.base import PerSymbolAlpha


class MACDHistogramAlpha(PerSymbolAlpha):
    """Normalized MACD histogram — trend strength + direction.

    Args:
        fast: Fast-EMA span (default 12).
        slow: Slow-EMA span (default 26).
        signal: Signal-line EMA span (default 9).
        hold_days: Insight close_time horizon.
    """

    name = "macd_histogram"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        hold_days: int = 5,
    ):
        self._fast = fast
        self._slow = slow
        self._signal = signal
        self.hold_days = hold_days

        # Reason: slow EMA needs ~slow bars to stabilize, then the
        # signal EMA layers on top of the macd series.
        self.lookback = slow + signal

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        closes = df["close"]

        ema_fast = closes.ewm(span=self._fast, adjust=False).mean()
        ema_slow = closes.ewm(span=self._slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self._signal, adjust=False).mean()

        hist = float(macd_line.iloc[-1] - signal_line.iloc[-1])
        price = float(closes.iloc[-1])

        if price <= 0.0 or not np.isfinite(hist):
            return None

        return hist / price
