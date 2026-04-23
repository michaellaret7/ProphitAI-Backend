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

This is the framework analog of the hand-rolled ``SignalCombiner`` +
``MagnitudeWeightedLongShort`` pair used in
``projects/qc_test/multi_alpha_daily/``. The inner PCM is swappable —
you can blend into EqualWeight, InsightWeighted, or any other PCM.
"""

from __future__ import annotations

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.portfolio_construction.base import (
    cross_sectional_zscore,
)
from prophitai_algo_trading.framework.protocols import PortfolioConstructionModel


class MultiAlphaBlendPCM:
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
        inner: PortfolioConstructionModel,
        winsor_at: float | None = 3.0,
    ):
        if not weights:
            raise ValueError("weights must be non-empty")

        self._weights = dict(weights)
        self._inner = inner
        self._winsor = winsor_at

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]:
        if not insights:
            return self._inner.create_targets(ctx, [])

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

        composite: dict[str, float] = {}

        for sym in all_symbols:
            total = 0.0

            for alpha_name, z_map in zscored_by_alpha.items():
                w = self._weights.get(alpha_name, 0.0)
                total += w * z_map.get(sym, 0.0)

            composite[sym] = total

        # Reason: use any incoming insight as a source for generated/close
        # times. Blended insights inherit the first real insight's
        # timestamps for consistency with whatever triggered this bar.
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

        return self._inner.create_targets(ctx, blended)
