"""Short-term reversal alpha.

The N-day return, negated. Stocks that have sharply outperformed in the
last ~5 trading days tend to mean-revert; stocks that have sharply
underperformed tend to bounce. The sign flip makes "recent loser" the
positive-direction (long) candidate.

Empirically orthogonal to 12-1 momentum because momentum skips this
exact window (its ``skip_days=21`` default). Stacking both alphas
captures medium-term trend AND short-term reversion simultaneously.
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.framework.models import AlgorithmContext, Insight


class ShortTermReversalAlpha:
    """Negated N-day return on daily closes.

    Args:
        lookback_days: Reversal window in trading days (default 5 = one
            trading week).
        hold_days: Informational ``close_time`` horizon. Reversals play
            out over a few days, so keep this short.
    """

    name = "reversal"

    def __init__(
        self,
        lookback_days: int = 5,
        hold_days: int = 3,
    ):
        self._lookback_days = lookback_days
        self._hold_days = hold_days

        # Reason: need lookback+1 closes so closes[-lookback-1] is the
        # start of the N-day return window.
        self.lookback = lookback_days + 1

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        insights: list[Insight] = []

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]

            start_price = float(closes.iloc[-(self._lookback_days + 1)])
            current = float(closes.iloc[-1])

            if start_price <= 0.0 or current <= 0.0:
                continue

            recent_return = (current / start_price) - 1.0

            # Reason: negate — recent loser is the long candidate,
            # recent winner is the short candidate.
            reversal_score = -recent_return

            direction = 1 if reversal_score > 0.0 else -1 if reversal_score < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(reversal_score),
                source_alpha=self.name,
            ))

        return insights
