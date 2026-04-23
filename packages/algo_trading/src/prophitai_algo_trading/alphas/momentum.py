"""12-1 cross-sectional price momentum alpha.

Classic Jegadeesh-Titman momentum: the return from t-(lookback) through
t-(skip). Skipping the most recent ~21 trading days avoids the
well-documented one-month reversal effect that otherwise contaminates
raw momentum signals.

Emits one Insight per ready symbol. Direction is the sign of the 12-1
return; magnitude is its absolute value. The PortfolioConstructionModel
cross-sectionally z-scores magnitude before blending with other alphas.
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.framework.models import AlgorithmContext, Insight


class MomentumAlpha:
    """12-1 price momentum.

    With defaults (lookback=252, skip=21), measures the return from 252
    trading days ago through 21 trading days ago. Requires lookback+1
    daily closes before emitting insights for a symbol.

    Args:
        lookback_days: Span of the return window in trading days.
        skip_days: Trailing days dropped from the measurement to avoid
            the short-term reversal effect (default 21 = one month).
        hold_days: Informational ``close_time`` horizon. PCMs may use
            this to keep targets alive between rebalances.
    """

    name = "momentum"

    def __init__(
        self,
        lookback_days: int = 252,
        skip_days: int = 21,
        hold_days: int = 5,
    ):
        self._lookback_days = lookback_days
        self._skip_days = skip_days
        self._hold_days = hold_days

        # Reason: need lookback+1 observations so closes[-lookback-1] exists.
        self.lookback = lookback_days + 1

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        insights: list[Insight] = []

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            closes = df["close"]

            start_price = float(closes.iloc[-(self._lookback_days + 1)])
            end_price = float(closes.iloc[-(self._skip_days + 1)])

            if start_price <= 0.0 or end_price <= 0.0:
                continue

            raw_return = (end_price / start_price) - 1.0

            direction = 1 if raw_return > 0.0 else -1 if raw_return < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(raw_return),
                source_alpha=self.name,
            ))

        return insights
