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

import pandas as pd

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.portfolio_construction.base import (
    BasePCM,
    BuildResult,
)
from prophitai_algo_trading.portfolio_construction.helpers import (
    dedupe_insights,
    weight_to_shares,
)
from prophitai_algo_trading.portfolio_construction.vector_helpers import (
    apply_cadence,
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

class InsightWeightedPCM(BasePCM):
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

        super().__init__(rebalance_every=rebalance_every)

        self._gross = gross_exposure
        self._cap = per_position_cap
        self._max = max_positions

    def _build(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> BuildResult:
        unique = dedupe_insights(insights)

        # Reason: feed *every* deduped insight into the score map so
        # the provenance tracker can split cohort_drop (no insight) from
        # magnitude_decay (insight present but didn't make the book).
        scores: dict[str, float] = {
            i.symbol: i.direction * (i.magnitude or 0.0) for i in unique
        }

        active = [i for i in unique if i.direction != 0]

        if not active:
            return BuildResult(targets=[], scores=scores)

        # Reason: rank + truncate before normalizing, so cap math sees
        # only the chosen cohort.
        scored = sorted(active, key=_extract_weight, reverse=True)

        if self._max is not None:
            scored = scored[: self._max]

        raw_weights = {i: _extract_weight(i) for i in scored}
        total = sum(raw_weights.values())

        if total <= 0:
            return BuildResult(targets=[], scores=scores)

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

        return BuildResult(
            targets=targets, contributions=contributions, scores=scores,
        )

    #     ================================
    # --> Vectorized PCM
    #     ================================

    def build_weights(
        self, scores: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Vectorized magnitude-proportional sizing with per-position cap.

        Per row:
            1. Collapse multi-alpha input by picking the largest
               ``|signed_score|`` per ticker.
            2. ``raw_weight = |signed_score| / sum(|signed_score|) * gross``
               then ``min(per_position_cap, raw)``.
            3. Apply original score sign so longs/shorts split out
               (no quantile cut — every directional name is sized).
            4. If ``max_positions`` is set, keep the top-N by
               ``|signed_score|`` first.

        Args:
            scores: ``{alpha_name: signed_score_panel}``.

        Returns:
            ``[date x ticker]`` signed weight panel, cadence-applied.
        """
        from prophitai_algo_trading.portfolio_construction.equal_weight import (
            _max_abs_pick,
        )

        composite = _max_abs_pick(scores)

        if composite.empty:
            return composite.copy()

        if self._max is not None:
            composite = _keep_top_n(composite, self._max)

        abs_score = composite.abs()
        row_total = abs_score.sum(axis=1)

        valid = row_total > 0.0

        normalized = abs_score.div(row_total.where(valid), axis=0) * self._gross

        normalized = normalized.fillna(0.0)
        normalized = normalized.clip(upper=self._cap)

        signed = normalized * _sign_panel(composite)

        return apply_cadence(signed, self._scheduler._every)


#     ================================
# --> Helper funcs (vectorized)
#     ================================

def _sign_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Element-wise sign — +1 / 0 / -1."""
    out = panel.copy()
    out[panel > 0] = 1.0
    out[panel < 0] = -1.0
    out[panel == 0] = 0.0

    return out


def _keep_top_n(panel: pd.DataFrame, n: int) -> pd.DataFrame:
    """Per row, zero out everything except the top-N by ``|value|``."""
    abs_panel = panel.abs()
    rank = abs_panel.rank(axis=1, method="first", ascending=False)

    keep = rank <= n

    return panel.where(keep, other=0.0)
