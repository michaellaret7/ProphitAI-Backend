"""MultiAlphaBlendPCM — blend insights from multiple alphas, then delegate.

The PCM that makes multi-alpha portfolios clean. Pipeline:

  1. Partition incoming insights by ``source_alpha``.
  2. For each alpha, cross-sectionally z-score its signed scores
     (direction * magnitude) and winsorize at ±3σ.
  3. Weighted-sum the z-scored values into a composite score per symbol,
     using the static ``weights`` dict.
  4. Synthesize a single list of "blended" Insights with the composite
     as magnitude and ``source_alpha='blended'``.
  5. Delegate to an inner PCM (typically MagnitudeWeightedLongShortPCM)
     for the actual target construction.
  6. Hand the inner's targets + per-symbol composite + per-alpha
     contributions to a ``ProvenanceTracker`` for ``entry_alphas`` /
     ``exit_reason`` enrichment. Any provenance the inner already
     stamped is overwritten — the outer has richer multi-alpha
     attribution than the inner can produce on synthesized "blended"
     insights.

This is the framework analog of the hand-rolled ``SignalCombiner`` +
``MagnitudeWeightedLongShort`` pair used in
``projects/qc_test/multi_alpha_daily/``. The inner PCM is swappable —
you can blend into EqualWeight, InsightWeighted, or any other PCM.
"""

from __future__ import annotations

import pandas as pd

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.core.protocols import (
    PortfolioConstructionModel,
    VectorPCM,
)
from prophitai_algo_trading.portfolio_construction.base import BasePCM
from prophitai_algo_trading.portfolio_construction.helpers import (
    cross_sectional_zscore,
)
from prophitai_algo_trading.portfolio_construction.vector_helpers import (
    zscore_rowwise,
)


class MultiAlphaBlendPCM(BasePCM):
    """Cross-sec z-score + weighted blend → inner PCM.

    Args:
        weights: {alpha_name: weight}. Not re-normalized — negative weights
            flip a signal's contribution; weights not summing to 1 tilt
            the blended magnitude scale.
        inner: A PortfolioConstructionModel that consumes the synthesized
            blended insights and produces targets. Typical choice:
            ``MagnitudeWeightedLongShortPCM``.
        winsor_at: z-score clip applied per-alpha after z-scoring.
            ``None`` disables winsorization.
    """

    def __init__(
        self,
        weights: dict[str, float],
        inner: PortfolioConstructionModel | VectorPCM,
        winsor_at: float | None = 3.0,
    ):
        if not weights:
            raise ValueError("weights must be non-empty")

        # Reason: rebalance_every=None — MAPM is a wrapper. Cadence
        # gating belongs to the inner PCM. The base's scheduler is
        # always-pass-through here (unused), but we still get
        # ``self._provenance`` from super().__init__() which is the
        # actual point of subclassing BasePCM.
        super().__init__(rebalance_every=None)

        self._weights = dict(weights)
        self._inner = inner
        self._winsor = winsor_at

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]:
        if not insights:
            inner_targets = self._inner.create_targets(ctx, [])

            return self._provenance.enrich(
                inner_targets, {}, {}, ctx.portfolio,
            )

        by_alpha: dict[str, list[Insight]] = {}

        for insight in insights:
            by_alpha.setdefault(insight.source_alpha, []).append(insight)

        zscored_by_alpha: dict[str, dict[str, float]] = {}

        for alpha_name, alpha_insights in by_alpha.items():
            signed = {
                i.symbol: i.direction * (i.magnitude or 0.0)
                for i in alpha_insights
            }
            zscored_by_alpha[alpha_name] = cross_sectional_zscore(
                signed, winsor_at=self._winsor,
            )

        all_symbols: set[str] = set()

        for z_map in zscored_by_alpha.values():
            all_symbols.update(z_map.keys())

        contributions: dict[str, dict[str, float]] = {}
        composite: dict[str, float] = {}

        for sym in all_symbols:
            per_alpha: dict[str, float] = {}
            total = 0.0

            for alpha_name, z_map in zscored_by_alpha.items():
                w = self._weights.get(alpha_name, 0.0)
                contrib = w * z_map.get(sym, 0.0)

                per_alpha[alpha_name] = contrib
                total += contrib

            contributions[sym] = per_alpha
            composite[sym] = total

        reference = insights[0]

        blended: list[Insight] = []

        for sym, score in composite.items():
            direction = 1 if score > 0.0 else -1 if score < 0.0 else 0

            blended.append(Insight(
                symbol=sym,
                direction=direction,
                generated_time=reference.generated_time,
                close_time=reference.close_time,
                magnitude=abs(score),
                source_alpha="blended",
            ))

        inner_targets = self._inner.create_targets(ctx, blended)

        return self._provenance.enrich(
            inner_targets, contributions, composite, ctx.portfolio,
        )

    #     ================================
    # --> Vectorized PCM
    #     ================================

    def build_weights(
        self, scores: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Vectorized z-score + weighted blend → inner vector PCM.

        Per alpha:
            1. Cross-sectional z-score per row (winsorize at ``winsor_at``).
            2. Multiply by configured static weight.
        Sum across alphas → composite score panel → hand to ``inner``
        as a single-entry dict ``{"blended": composite}``. Inner PCM
        does its own ranking / sizing / cadence.

        Args:
            scores: ``{alpha_name: signed_score_panel}``.

        Returns:
            ``[date x ticker]`` signed weight panel from the inner PCM.
        """
        if not scores:
            raise ValueError("MultiAlphaBlendPCM.build_weights got no scores")

        first = next(iter(scores.values()))

        composite = pd.DataFrame(
            0.0, index=first.index, columns=first.columns,
        )

        for alpha_name, panel in scores.items():
            weight = self._weights.get(alpha_name, 0.0)

            if weight == 0.0:
                continue

            zscored = zscore_rowwise(panel, winsor_at=self._winsor)

            composite = composite.add(zscored * weight, fill_value=0.0)

        return self._inner.build_weights({"blended": composite})
