"""3-bar micro-momentum alpha (intraday continuation).

Sub-day persistence: a 3-bar return at hourly resolution captures the
~3-hour momentum that institutional flow tends to extend across the
session. Distinct from daily 12-1 momentum (which works on a months
horizon) — this is a true intraday persistence signal.

    score = (close[t] / close[t-3]) - 1

Positive score → continuation expected (long). Negative → continue
short. The horizon is short enough that sign-changes happen multiple
times per session.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class MicroMomentumAlpha(PerSymbolAlpha):
    """3-bar return continuation."""

    name = "micro_momentum"

    def __init__(
        self,
        return_window: int = 3,
        hold_days: int = 1,
    ):
        self._window = return_window
        self.hold_days = hold_days
        self.lookback = return_window + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        start_price = float(closes.iloc[-(self._window + 1)])
        current = float(closes.iloc[-1])

        if start_price <= 0.0 or current <= 0.0:
            return None

        return (current / start_price) - 1.0

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        return panel.close.pct_change(self._window)
