"""InsightWeightedPCM — size positions proportional to insight magnitude.

One step up from EqualWeightPCM. Every directional insight gets a
position sized by |magnitude| / sum(|magnitude|) * gross_exposure. High-
conviction insights get more capital than low-conviction ones.

Uses the insight's ``weight`` field when provided (lets an alpha emit
explicit per-symbol weight hints), falling back to ``magnitude``. If
neither is set, a symbol is treated as weight 1 (effectively equal-weight
alongside other weight-less insights).
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.portfolio_construction.helpers import (
    RebalanceScheduler,
    append_close_orphans,
    dedupe_insights,
    weight_to_shares,
)
from prophitai_algo_trading.portfolio_construction.provenance import (
    ProvenanceTracker,
)


#     ================================
# --> Helper funcs
#     ================================

def _extract_weight(insight: Insight) -> float:
    """Pick the size-intent from insight.weight, fall back to magnitude."""
    if insight.weight is not None:
        return abs(insight.weight)

    if insight.magnitude is not None:
        return abs(insight.magnitude)

    return 1.0


#     ================================
# --> PCM
#     ================================

class InsightWeightedPCM:
    """Magnitude-proportional sizing with an optional per-position cap.

    Args:
        gross_exposure: Total absolute weight across all positions.
        per_position_cap: Maximum absolute weight for any single name.
            Prevents one monster-insight from dominating the book. Use
            ``1.0`` to disable.
        max_positions: Optional cap. ``None`` = no cap; keep every
            directional insight.
        rebalance_every: ``timedelta`` between rebalances. ``None`` = every
            bar.
    """

    def __init__(
        self,
        gross_exposure: float = 1.0,
        per_position_cap: float = 0.10,
        max_positions: int | None = None,
        rebalance_every: timedelta | None = None,
    ):
        if gross_exposure <= 0:
            raise ValueError("gross_exposure must be > 0")
        if per_position_cap <= 0 or per_position_cap > 1.0:
            raise ValueError("per_position_cap must be in (0, 1]")

        self._gross = gross_exposure
        self._cap = per_position_cap
        self._max = max_positions
        self._scheduler = RebalanceScheduler(rebalance_every)
        self._provenance = ProvenanceTracker()

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]:
        if not self._scheduler.is_rebalance_bar(ctx.timestamp):
            return []

        unique = dedupe_insights(insights)

        # Reason: feed *every* deduped insight into the score map so
        # the provenance tracker can split cohort_drop (no insight) from
        # magnitude_decay (insight present but didn't make the book).
        scores: dict[str, float] = {
            i.symbol: i.direction * (i.magnitude or 0.0) for i in unique
        }

        active = [i for i in unique if i.direction != 0]

        if not active:
            return self._enrich(ctx, append_close_orphans(ctx, []), {}, scores)

        # Reason: rank + truncate before normalizing, so cap math sees
        # only the chosen cohort.
        scored = sorted(active, key=_extract_weight, reverse=True)

        if self._max is not None:
            scored = scored[: self._max]

        raw_weights = {i: _extract_weight(i) for i in scored}
        total = sum(raw_weights.values())

        if total <= 0:
            return self._enrich(ctx, append_close_orphans(ctx, []), {}, scores)

        targets: list[PortfolioTarget] = []
        contributions: dict[str, dict[str, float]] = {}

        for insight, raw in raw_weights.items():
            # Reason: normalize to sum to gross, then cap per-position.
            weight = (raw / total) * self._gross
            weight = min(weight, self._cap)

            shares = weight_to_shares(
                ctx, insight.symbol, weight, insight.direction,
            )

            if shares is None:
                continue

            targets.append(PortfolioTarget(
                symbol=insight.symbol, target_shares=shares,
            ))
            contributions[insight.symbol] = {insight.source_alpha: 1.0}

        return self._enrich(
            ctx, append_close_orphans(ctx, targets), contributions, scores,
        )

    def _enrich(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
        contributions: dict[str, dict[str, float]],
        scores: dict[str, float],
    ) -> list[PortfolioTarget]:
        return self._provenance.enrich(
            targets, contributions, scores, ctx.portfolio,
        )
