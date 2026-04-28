"""Overnight-drift alpha — sum of overnight returns over a window.

Lou, Polk & Skouras (2018, JFE "A Tug of War: Overnight Versus Intraday
Returns") and Berkman et al. (2012) documented that the overnight
component of returns ``(open_t - close_{t-1}) / close_{t-1}`` carries
a persistent positive premium for many stocks. Cumulating overnight
returns over a rolling window picks out names with steady "after-hours
buyer" flow.

    overnight_t = (open_t - close_{t-1}) / close_{t-1}
    score       = sum(overnight over past N bars)

Distinct from ``GapFadeAlpha`` (which negates a single recent gap):
this is the *cumulative* overnight return — a slow-moving, trend-style
signal. The two are designed to capture opposite phenomena: fade
single-day extremes vs. ride persistent multi-week overnight drift.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class OvernightDriftAlpha(PerSymbolAlpha):
    """Rolling sum of overnight returns.

    Args:
        lookback_days: Window over which overnight returns are summed
            (default 21 = ~one trading month).
        hold_days: Informational ``close_time`` horizon. Overnight
            premia are slow-decay.
    """

    name = "overnight_drift"
    required_columns = ("open", "close")

    def __init__(
        self,
        lookback_days: int = 21,
        hold_days: int = 21,
    ):
        self._window = lookback_days
        self.hold_days = hold_days

        # Reason: need lookback+1 closes so the first overnight return
        # has a prev_close.
        self.lookback = lookback_days + 1

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        opens = df["open"].iloc[-self._window:]
        prev_closes = df["close"].shift(1).iloc[-self._window:]

        if prev_closes.isna().any() or (prev_closes <= 0.0).any():
            return None

        overnight = (opens / prev_closes) - 1.0

        if overnight.isna().any():
            return None

        return float(overnight.sum())

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized sum of overnight returns across the panel."""
        if panel.open is None:
            raise ValueError(
                "OvernightDriftAlpha.compute_panel requires panel.open",
            )

        prev_close = panel.close.shift(1)

        overnight = (panel.open / prev_close.where(prev_close > 0.0)) - 1.0

        return overnight.rolling(self._window).sum()
