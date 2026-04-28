"""MagnitudeWeightedLongShortConstructor — decile-cut dollar-neutral L/S builder.

Takes per-symbol insights and builds a long/short book:
  1. Rank by signed score (``direction * magnitude``).
  2. Take top ``quantile`` as longs, bottom ``quantile`` as shorts.
  3. Filter by ``min_abs_score`` so thin-signal days don't trade.
  4. Within each side, weight by |signed score| (conviction-weighted).
  5. Rescale sides to the smaller side's total, enforcing dollar neutrality.
  6. Cap per-position at ``per_position_cap``.

This is the PCM from ``projects/qc_test/multi_alpha_daily/custom_portfolio.py``
repositioned into the framework. It's the workhorse for cross-sectional
long/short strategies.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.construction.base import (
    BaseConstructor,
    BuildResult,
)
from prophitai_algo_trading.construction.helpers.event import (
    weight_to_shares,
)
from prophitai_algo_trading.construction.helpers.vector import (
    apply_cadence,
    rank_to_long_short_weights,
)


#     ================================
# --> Helper funcs
#     ================================

def _side_weights(
    side: list[tuple[str, float]],
    side_budget: float,
    per_position_cap: float,
) -> dict[str, float]:
    """Magnitude-proportional weights for one side, capped per name.

    Args:
        side: list of ``(symbol, signed_score)`` — all scores same sign.
        side_budget: target unsigned gross for this side.
        per_position_cap: maximum unsigned weight per symbol.
    """
    total_abs = sum(abs(s) for _, s in side)

    if total_abs <= 0.0:
        return {}

    weights: dict[str, float] = {}

    for sym, s in side:
        raw = side_budget * (abs(s) / total_abs)
        weights[sym] = min(per_position_cap, raw)

    return weights


def _rescale_to_neutral(
    long_weights: dict[str, float],
    short_weights: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    """Rescale both sides so |sum(long)| == |sum(short)|.

    Per-position caps can leave the two sides asymmetric. We shrink the
    larger side to match the smaller, preserving dollar-neutrality at
    the portfolio level.
    """
    long_sum = sum(long_weights.values())
    short_sum = sum(short_weights.values())

    neutral = min(long_sum, short_sum)

    if neutral <= 0.0:
        return {}, {}

    long_scale = neutral / long_sum if long_sum > 0 else 1.0
    short_scale = neutral / short_sum if short_sum > 0 else 1.0

    scaled_longs = {s: w * long_scale for s, w in long_weights.items()}
    scaled_shorts = {s: w * short_scale for s, w in short_weights.items()}

    return scaled_longs, scaled_shorts


#     ================================
# --> PCM
#     ================================

class MagnitudeWeightedLongShortConstructor(BaseConstructor):
    """Decile-cut magnitude-weighted dollar-neutral builder.

    Args:
        gross_exposure: Total L + S absolute exposure as a fraction of
            equity (2.0 = 200% gross = 100% long + 100% short).
        per_position_cap: Max unsigned weight per single position.
        quantile: Fraction of the ranked universe taken per side
            (0.10 = decile cut = top 10% long + bottom 10% short).
        min_abs_score: Signed-score magnitude threshold. Names with
            ``abs(direction * magnitude) < min_abs_score`` are dropped —
            prevents trading on weak signals.
        rebalance_every: ``timedelta`` between rebalances. ``None`` =
            every bar.
    """

    def __init__(
        self,
        gross_exposure: float = 2.0,
        per_position_cap: float = 0.10,
        quantile: float = 0.10,
        min_abs_score: float = 0.20,
        rebalance_every: timedelta | None = None,
    ):
        if gross_exposure <= 0:
            raise ValueError("gross_exposure must be > 0")
        if not 0.0 < per_position_cap <= 1.0:
            raise ValueError("per_position_cap must be in (0, 1]")
        if not 0.0 < quantile <= 0.5:
            raise ValueError("quantile must be in (0, 0.5]")

        super().__init__(rebalance_every=rebalance_every)

        self._gross = gross_exposure
        self._cap = per_position_cap
        self._quantile = quantile
        self._min_abs = min_abs_score

    def _build(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> BuildResult:
        # Reason: one insight per symbol by construction (the PCM upstream
        # of this — e.g. MultiAlphaBlender — deduplicates). Use whatever
        # comes in; if multiple exist for a symbol, the last wins.
        signed: dict[str, float] = {
            i.symbol: i.direction * (i.magnitude or 0.0)
            for i in insights
        }
        source_by_symbol: dict[str, str] = {
            i.symbol: i.source_alpha for i in insights
        }

        if not signed:
            return BuildResult(targets=[], scores=signed)

        ranked = sorted(signed.items(), key=lambda kv: kv[1])

        n = len(ranked)
        k = max(1, int(n * self._quantile))

        shorts_side = [
            (sym, s) for sym, s in ranked[:k] if s <= -self._min_abs
        ]
        longs_side = [
            (sym, s) for sym, s in ranked[-k:] if s >= self._min_abs
        ]

        if not longs_side or not shorts_side:
            return BuildResult(targets=[], scores=signed)

        side_budget = self._gross / 2.0

        long_weights = _side_weights(longs_side, side_budget, self._cap)
        short_weights = _side_weights(shorts_side, side_budget, self._cap)

        long_scaled, short_scaled = _rescale_to_neutral(
            long_weights, short_weights,
        )

        if not long_scaled or not short_scaled:
            return BuildResult(targets=[], scores=signed)

        targets: list[PortfolioTarget] = []
        contributions: dict[str, dict[str, float]] = {}

        for sym, weight in long_scaled.items():
            shares = weight_to_shares(ctx, sym, weight, direction=1)

            if shares is None:
                continue

            targets.append(PortfolioTarget(symbol=sym, target_shares=shares))
            contributions[sym] = {source_by_symbol[sym]: 1.0}

        for sym, weight in short_scaled.items():
            shares = weight_to_shares(ctx, sym, weight, direction=-1)

            if shares is None:
                continue

            targets.append(PortfolioTarget(symbol=sym, target_shares=shares))
            contributions[sym] = {source_by_symbol[sym]: 1.0}

        return BuildResult(
            targets=targets, contributions=contributions, scores=signed,
        )

    #     ================================
    # --> Vectorized PCM
    #     ================================

    def build_weights(
        self, scores: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """Vectorized decile-cut magnitude-weighted dollar-neutral builder.

        Multi-alpha input is collapsed by picking the ``|signed_score|``
        max per ticker (matches event-driven ``dedupe_insights``).
        Then per row: rank → quantile cut → magnitude-weighted sizing
        with per-position cap and cross-side rescale to dollar-neutral.

        Args:
            scores: ``{alpha_name: signed_score_panel}``.

        Returns:
            ``[date x ticker]`` signed weight panel, cadence-applied.
        """
        from prophitai_algo_trading.construction.equal_weight import (
            _max_abs_pick,
        )

        composite = _max_abs_pick(scores)

        weights = rank_to_long_short_weights(
            composite,
            quantile=self._quantile,
            gross_exposure=self._gross,
            per_position_cap=self._cap,
            min_abs_score=self._min_abs,
        )

        return apply_cadence(weights, self._scheduler._every)
