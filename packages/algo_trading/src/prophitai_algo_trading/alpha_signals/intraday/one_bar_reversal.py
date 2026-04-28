"""One-bar reversal alpha (intraday liquidity-provision premium).

At hourly granularity, a single-bar return often overshoots fair value
due to short-bursts of order imbalance — the next bar tends to retrace
some of the move as fresh liquidity arrives. The signal:

    score = -((close[t] - close[t-1]) / close[t-1])

Negate today's bar return so the bar that just spiked up becomes a
short candidate, and the bar that just dumped becomes a long candidate.
Distinct from a multi-bar reversal because it specifically captures
the one-bar overshoot mechanism.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


class OneBarReversalAlpha(PerSymbolAlpha):
    """Negated last-bar return."""

    name = "one_bar_reversal"

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days
        self.lookback = 2

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        closes = df["close"]

        prev_close = float(closes.iloc[-2])
        cur_close = float(closes.iloc[-1])

        if prev_close <= 0.0 or cur_close <= 0.0:
            return None

        return -((cur_close / prev_close) - 1.0)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        return -panel.close.pct_change(1)
