"""MagnitudeWeightedLongShortPCM — decile-cut dollar-neutral L/S builder.

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

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    Insight,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.portfolio_construction.base import (
    RebalanceScheduler,
    append_close_orphans,
    weight_to_shares,
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

class MagnitudeWeightedLongShortPCM:
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

        self._gross = gross_exposure
        self._cap = per_position_cap
        self._quantile = quantile
        self._min_abs = min_abs_score
        self._scheduler = RebalanceScheduler(rebalance_every)

    def create_targets(
        self,
        ctx: AlgorithmContext,
        insights: list[Insight],
    ) -> list[PortfolioTarget]:
        if not self._scheduler.is_rebalance_bar(ctx.timestamp):
            return []

        # Reason: one insight per symbol by construction (the PCM upstream
        # of this — e.g. MultiAlphaBlendPCM — deduplicates). Use whatever
        # comes in; if multiple exist for a symbol, the last wins.
        signed: dict[str, float] = {
            i.symbol: i.direction * (i.magnitude or 0.0)
            for i in insights
        }

        if not signed:
            return append_close_orphans(ctx, [])

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
            return append_close_orphans(ctx, [])

        side_budget = self._gross / 2.0

        long_weights = _side_weights(longs_side, side_budget, self._cap)
        short_weights = _side_weights(shorts_side, side_budget, self._cap)

        long_scaled, short_scaled = _rescale_to_neutral(long_weights, short_weights)

        if not long_scaled or not short_scaled:
            return append_close_orphans(ctx, [])

        targets: list[PortfolioTarget] = []

        for sym, weight in long_scaled.items():
            shares = weight_to_shares(ctx, sym, weight, direction=1)

            if shares is None:
                continue

            targets.append(PortfolioTarget(symbol=sym, target_shares=shares))

        for sym, weight in short_scaled.items():
            shares = weight_to_shares(ctx, sym, weight, direction=-1)

            if shares is None:
                continue

            targets.append(PortfolioTarget(symbol=sym, target_shares=shares))

        return append_close_orphans(ctx, targets)
