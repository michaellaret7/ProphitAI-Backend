"""MaxGrossExposureRiskModel — hard cap on portfolio gross notional.

Final guard against oversized books. Computes
``sum(|target_shares| * price)`` over every target; if that gross
exceeds ``max_gross * equity``, scale every target proportionally down
so the post-scale gross exactly equals the cap.

Typically runs last in a CompositeRiskModel so any delever or stop-loss
adjustments from earlier stages are respected in the final gross math.

Not a ``RiskRule`` — operates on the *list* of targets (proportional
scaling), which falls outside the per-symbol hook surface. Lives
alongside the rules as a standalone ``RiskManagementModel``.
"""

from __future__ import annotations

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    PortfolioTarget,
)


#     ================================
# --> Helper funcs
#     ================================

def _target_notional(
    ctx: AlgorithmContext, target: PortfolioTarget,
) -> float:
    """Return |shares * last_close| for a target. 0 if price unavailable."""
    df = ctx.data.get(target.symbol)

    if df is None or df.empty:
        return 0.0

    price = float(df["close"].iloc[-1])

    if price <= 0.0:
        return 0.0

    return abs(target.target_shares) * price


#     ================================
# --> Risk model
#     ================================

class MaxGrossExposureRiskModel:
    """Downscale all targets proportionally to respect a gross cap."""

    def __init__(self, max_gross: float = 2.0):
        if max_gross <= 0:
            raise ValueError("max_gross must be > 0")

        self._max_gross = max_gross

    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        if not targets:
            return list(targets)

        equity = ctx.portfolio.equity()

        if equity <= 0:
            return list(targets)

        gross_notional = sum(_target_notional(ctx, t) for t in targets)

        gross_ratio = gross_notional / equity

        if gross_ratio <= self._max_gross:
            return list(targets)

        scale = self._max_gross / gross_ratio

        return [
            PortfolioTarget(
                symbol=t.symbol,
                target_shares=t.target_shares * scale,
            )
            for t in targets
        ]
