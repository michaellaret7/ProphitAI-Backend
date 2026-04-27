"""Equal-weight PCM — pick top-N by |signed score|, equal within each side.

Simplest usable PCM. No magnitude-weighting, no sector logic, no vol
targeting — just "rank the insights, pick the most confident ones, split
the book evenly across them."

Use when you want a sanity baseline or when the alpha's magnitudes are
so noisy that equal-weighting beats magnitude-weighting.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.construction.base import (
    BasePCM,
    BuildResult,
)
from prophitai_algo_trading.construction.helpers.event import (
    dedupe_insights,
    weight_to_shares,
)
from prophitai_algo_trading.construction.helpers.vector import (
    apply_cadence,
)


class EqualWeightPCM(BasePCM):
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

        super().__init__(rebalance_every=rebalance_every)

        self._max = max_positions
        self._gross = gross_exposure

    def _build(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> BuildResult:
        unique = dedupe_insights(insights)

        # Reason: feed *every* deduped insight into the score map so
        # the provenance tracker can split cohort_drop (no insight) from
        # magnitude_decay (insight present but didn't make the top-N).
        scores: dict[str, float] = {
            i.symbol: i.direction * (i.magnitude or 0.0) for i in unique
        }

        scored = [(i, scores[i.symbol]) for i in unique if i.direction != 0]

        if not scored:
            return BuildResult(targets=[], scores=scores)

        # Reason: |signed_score| picks most extreme regardless of sign.
        scored.sort(key=lambda pair: abs(pair[1]), reverse=True)

        chosen = scored[: self._max]

        if not chosen:
            return BuildResult(targets=[], scores=scores)

        per_position_weight = self._gross / len(chosen)

        targets: list[PortfolioTarget] = []
        contributions: dict[str, dict[str, float]] = {}

        for insight, _score in chosen:
            shares = weight_to_shares(
                ctx, insight.symbol, per_position_weight, insight.direction,
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
        """Vectorized top-N equal-weight construction.

        Per row: take the ``max_positions`` tickers with the largest
        ``|signed_score|``, split ``gross_exposure`` equally, sign by
        the original score sign. Multi-alpha input is collapsed by
        picking the alpha with the largest ``|signed_score|`` per ticker
        (matches event-driven ``dedupe_insights`` semantics).

        Args:
            scores: ``{alpha_name: signed_score_panel}``. All panels
                share the same index and columns.

        Returns:
            ``[date x ticker]`` weight panel, cadence-applied.
        """
        composite = _max_abs_pick(scores)

        if composite.empty:
            return composite.copy()

        index = composite.index
        columns = composite.columns

        score_arr = composite.to_numpy(dtype=float, copy=True)
        weight_arr = np.zeros_like(score_arr)

        per_position = self._gross / self._max

        for row_idx in range(score_arr.shape[0]):
            row = score_arr[row_idx]

            finite_mask = np.isfinite(row) & (row != 0.0)

            if not finite_mask.any():
                continue

            finite_idx = np.where(finite_mask)[0]
            finite_scores = row[finite_idx]

            n_pick = min(self._max, finite_idx.size)

            top_local = np.argsort(np.abs(finite_scores))[-n_pick:]

            chosen = finite_idx[top_local]
            chosen_scores = row[chosen]

            signs = np.sign(chosen_scores)

            weight_arr[row_idx, chosen] = signs * per_position

        weights = pd.DataFrame(weight_arr, index=index, columns=columns)

        return apply_cadence(weights, self._scheduler._every)


#     ================================
# --> Helper funcs (vectorized)
#     ================================

def _max_abs_pick(
    scores: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Collapse ``{alpha: panel}`` to one panel by picking the largest
    ``|score|`` per (date, ticker)."""
    if not scores:
        raise ValueError("scores dict is empty")

    panels = list(scores.values())

    composite = panels[0].copy()

    for other in panels[1:]:
        # Reason: keep the value whose |.| is larger; ties prefer existing.
        replace_mask = other.abs() > composite.abs()
        composite = composite.where(~replace_mask, other=other)

    return composite
