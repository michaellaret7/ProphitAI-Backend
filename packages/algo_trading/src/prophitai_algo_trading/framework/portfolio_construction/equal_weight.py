"""Equal-weight PCM — pick top-N by |signed score|, equal within each side.

Simplest usable PCM. No magnitude-weighting, no sector logic, no vol
targeting — just "rank the insights, pick the most confident ones, split
the book evenly across them."

Use when you want a sanity baseline or when the alpha's magnitudes are
so noisy that equal-weighting beats magnitude-weighting.
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.portfolio_construction.base import (
    RebalanceScheduler,
    append_close_orphans,
    dedupe_insights,
    weight_to_shares,
)


class EqualWeightPCM:
    """Top-N equal-weight construction.

    Ranks insights by ``direction * magnitude`` (signed score), picks the
    ``max_positions`` most extreme, and splits ``gross_exposure`` equally
    among them. Longs and shorts both land in the same N — so if the alpha
    emits 8 long + 12 short insights and ``max_positions=10``, you get the
    5 strongest of each side.

    Args:
        max_positions: Maximum concurrent open positions across both sides.
            Default 10.
        gross_exposure: Total absolute weight across all positions. 1.0 =
            fully invested one-sided or half-long/half-short. 2.0 = 2x
            levered L/S.
        rebalance_every: ``timedelta`` between rebalances. ``None`` = every
            bar (not recommended — causes heavy turnover).
    """

    def __init__(
        self,
        max_positions: int = 10,
        gross_exposure: float = 1.0,
        rebalance_every: timedelta | None = None,
    ):
        if max_positions <= 0:
            raise ValueError("max_positions must be > 0")
        if gross_exposure <= 0:
            raise ValueError("gross_exposure must be > 0")

        self._max = max_positions
        self._gross = gross_exposure
        self._scheduler = RebalanceScheduler(rebalance_every)

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]:
        if not self._scheduler.is_rebalance_bar(ctx.timestamp):
            return []

        unique = dedupe_insights(insights)

        scored = [
            (i, i.direction * (i.magnitude or 0.0))
            for i in unique
            if i.direction != 0
        ]

        if not scored:
            return append_close_orphans(ctx, [])

        # Reason: |signed_score| picks most extreme regardless of sign.
        scored.sort(key=lambda pair: abs(pair[1]), reverse=True)

        chosen = scored[: self._max]

        if not chosen:
            return append_close_orphans(ctx, [])

        per_position_weight = self._gross / len(chosen)

        targets: list[PortfolioTarget] = []

        for insight, _score in chosen:
            shares = weight_to_shares(
                ctx, insight.symbol, per_position_weight, insight.direction,
            )

            if shares is None:
                continue

            targets.append(PortfolioTarget(
                symbol=insight.symbol, target_shares=shares,
            ))

        return append_close_orphans(ctx, targets)
