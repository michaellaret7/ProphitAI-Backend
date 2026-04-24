"""Bollinger Band mean-reversion alpha.

Position inside Bollinger(20, 2σ) bands, inverted for mean reversion.

    band_position = (close - sma_20) / (2 * sigma_20)
    score = -band_position   (clipped to ±1)

    close near lower band -> +1 (long)
    close at SMA          ->  0
    close near upper band -> -1 (short)

Clipping prevents a runaway breakout from emitting an absurd magnitude
that would dominate the multi-alpha blend.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_algo_trading.alphas.base import PerSymbolAlpha


class BollingerBandReversionAlpha(PerSymbolAlpha):
    """Inverted band position — contrarian bet toward the mean.

    Args:
        lookback_days: Window for the SMA + sigma (default 20).
        num_std: Band width in standard deviations (default 2.0).
        hold_days: Insight close_time horizon.
    """

    name = "bollinger_reversion"

    def __init__(
        self,
        lookback_days: int = 20,
        num_std: float = 2.0,
        hold_days: int = 5,
    ):
        self._window = lookback_days
        self._num_std = num_std
        self.hold_days = hold_days
        self.lookback = lookback_days

    def compute_score(self, df: pd.DataFrame) -> float | None:
        closes = df["close"]
        window = closes.iloc[-self._window:]

        sma = float(window.mean())
        sigma = float(window.std(ddof=1))

        if sigma <= 0.0 or not np.isfinite(sigma):
            return None

        current = float(closes.iloc[-1])

        band_position = (current - sma) / (self._num_std * sigma)

        clipped = max(-1.0, min(1.0, band_position))

        return -clipped
