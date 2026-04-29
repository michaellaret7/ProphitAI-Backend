"""Range-compression alpha — squeeze setup, signed by recent direction.

Average True Range (ATR) over a short window divided by ATR over a long
window. Ratios well below 1 mean the recent range is compressed
relative to the long-run norm — historically this presages a
volatility expansion (a range "squeeze release"). Direction is the
sign of the recent close-to-close return: the squeeze is most likely
to break the way the price is already leaning.

    tr             = max(high - low, |high - prev_close|, |low - prev_close|)
    atr_short      = mean(tr over short_window)
    atr_long       = mean(tr over long_window)
    compression    = max(0, 1 - atr_short / atr_long)
    direction      = sign(close[t] / close[t - direction_window] - 1)
    score          = compression * direction

Score is non-zero only when the range is genuinely compressed AND there
is a directional lean. Uncompressed names (ratio >= 1) emit zero.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha
from prophitai_algo_trading.alpha_signals.helpers.true_range import (
    true_range_panel,
    true_range_series,
)

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Alpha
#     ================================

class RangeCompressionAlpha(PerSymbolAlpha):
    """Squeeze-release setup: compressed ATR ratio signed by recent return.

    Args:
        short_window: Short ATR window in trading days (default 5).
        long_window: Long ATR window in trading days (default 60).
        direction_window: Lookback for the direction sign (default 10).
        hold_days: Informational ``close_time`` horizon — squeeze
            releases play out over a couple of weeks.
    """

    name = "range_compression"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 60,
        direction_window: int = 10,
        hold_days: int = 10,
    ):
        if short_window >= long_window:
            raise ValueError(
                f"short_window ({short_window}) must be < long_window "
                f"({long_window})",
            )

        self._short = short_window
        self._long = long_window
        self._dir = direction_window
        self.hold_days = hold_days

        # Reason: long ATR window plus one bar for the prev_close shift.
        self.lookback = long_window + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        tr = true_range_series(df).iloc[-self._long:]

        if len(tr) < self._long:
            return None

        atr_short = float(tr.iloc[-self._short:].mean())
        atr_long = float(tr.mean())

        if atr_long <= 0.0:
            return None

        compression = max(0.0, 1.0 - atr_short / atr_long)

        closes = df["close"]

        start_price = float(closes.iloc[-(self._dir + 1)])
        current = float(closes.iloc[-1])

        if start_price <= 0.0 or current <= 0.0:
            return None

        recent_return = current / start_price - 1.0
        direction = 1.0 if recent_return > 0.0 else -1.0 if recent_return < 0.0 else 0.0

        return compression * direction

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized range-compression score across the full panel.

        Computes per-ticker true range, short and long rolling ATRs,
        compression magnitude, and signs by direction-window return.
        """
        if panel.high is None or panel.low is None:
            raise ValueError(
                "RangeCompressionAlpha.compute_panel requires panel.high and "
                "panel.low",
            )

        tr = true_range_panel(panel.high, panel.low, panel.close)

        atr_short = tr.rolling(self._short).mean()
        atr_long = tr.rolling(self._long).mean()

        ratio = atr_short / atr_long.where(atr_long > 0.0)

        compression = (1.0 - ratio).clip(lower=0.0).fillna(0.0)

        direction = np.sign(panel.close.pct_change(self._dir).fillna(0.0))

        return compression * direction
