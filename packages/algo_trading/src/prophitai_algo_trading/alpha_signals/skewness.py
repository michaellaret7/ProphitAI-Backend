"""Return skewness alpha.

Harvey & Siddique (2000, J. Finance "Conditional Skewness in Asset
Pricing Tests") showed that investors overpay for positive-skew stocks
(rare but big upside payoffs). The signal is the *negated* rolling
skewness of daily returns: short positive-skew names, long negative-
skew names (which carry a premium because their downside is concentrated
and thus mispriced).

    score = - skewness(daily_returns over N bars)

Distinct from realized vol (a 2nd-moment measure) and from MAX (a
single-tail extreme): skewness is the asymmetry of the *full*
distribution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class SkewnessAlpha(PerSymbolAlpha):
    """Negated rolling skewness of daily returns.

    Args:
        lookback_days: Window for the skew estimate (default 60).
        hold_days: Informational ``close_time`` horizon — skewness
            premia are slow-decay.
    """

    name = "skewness"

    def __init__(
        self,
        lookback_days: int = 60,
        hold_days: int = 21,
    ):
        self._window = lookback_days
        self.hold_days = hold_days

        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        returns = df["close"].pct_change().iloc[-self._window:].dropna()

        if len(returns) < max(10, self._window // 2):
            return None

        skew = float(returns.skew())

        if not np.isfinite(skew):
            return None

        return -skew

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized negated rolling skew across the panel."""
        returns = panel.close.pct_change()

        return -returns.rolling(self._window).skew()
