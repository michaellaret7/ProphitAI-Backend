"""RSI mean-reversion alpha.

Classic Wilder RSI(14) inverted around 50. Oversold readings become
long candidates; overbought readings become short candidates.

    score = (50 - RSI) / 50

    RSI = 30 ->  +0.4   (oversold, long)
    RSI = 50 ->   0.0   (neutral)
    RSI = 70 ->  -0.4   (overbought, short)

Short-horizon mean-reversion signal. Decays in 2-5 bars so ``hold_days``
stays tight.
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.alphas.base import PerSymbolAlpha


class RSIMeanReversionAlpha(PerSymbolAlpha):
    """Wilder RSI inverted around 50 — contrarian short-horizon signal.

    Args:
        lookback_days: RSI period (default 14 — Wilder's original).
        hold_days: Insight close_time horizon.
    """

    name = "rsi_reversion"

    def __init__(self, lookback_days: int = 14, hold_days: int = 3):
        self._window = lookback_days
        self.hold_days = hold_days
        # Reason: need window+1 closes so the first delta exists.
        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        closes = df["close"]

        deltas = closes.diff().iloc[-self._window:]

        gains = deltas.clip(lower=0.0)
        losses = (-deltas).clip(lower=0.0)

        avg_gain = float(gains.mean())
        avg_loss = float(losses.mean())

        if avg_loss == 0.0 and avg_gain == 0.0:
            return None

        if avg_loss == 0.0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - 100.0 / (1.0 + rs)

        return (50.0 - rsi) / 50.0
