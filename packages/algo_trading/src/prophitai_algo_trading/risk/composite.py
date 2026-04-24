"""CompositeRiskModel — sequential composition of RiskManagementModels.

Each model sees the output of the previous. Order matters:
  1. Put portfolio-wide circuit breakers first (drawdown halt, daily
     loss) so they zero targets before finer rules get to work on them.
  2. Put gross-cap last so it's the final guard against any upstream
     model accidentally producing an oversized book.

Every concrete ``RiskRule`` (stops, trails, cooldowns, limits, windows)
is itself a full ``RiskManagementModel`` — drop rules directly into the
composite alongside the standalone portfolio models:

    risk = CompositeRiskModel([
        MaxDrawdownRiskModel(max_drawdown_pct=0.15, delever_factor=0.5),
        DailyLossLimit(loss_pct=0.03),
        StopLossExit(pct=0.05),
        MaxGrossExposureRiskModel(max_gross=2.0),
    ])

Composite always advertises the ``LifecycleAwareRiskModel`` protocol;
individual children opt in structurally, and the engine's lifecycle
events fan out via per-child ``isinstance`` checks.
"""

from __future__ import annotations

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    PortfolioTarget,
)
from prophitai_algo_trading.core.protocols import (
    LifecycleAwareRiskModel,
    RiskManagementModel,
)


class CompositeRiskModel:
    """Runs a list of RiskManagementModels in sequence."""

    def __init__(self, models: list[RiskManagementModel]):
        if not models:
            raise ValueError("CompositeRiskModel requires at least one model")

        self._models = list(models)

    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        current = list(targets)

        for model in self._models:
            current = model.manage(ctx, current)

        return current

    #     ================================
    # --> Lifecycle forwarding
    #     ================================

    def on_position_opened(
        self, ctx: AlgorithmContext, symbol: str,
    ) -> None:
        """Forward to every child that satisfies ``LifecycleAwareRiskModel``."""
        for model in self._models:
            if isinstance(model, LifecycleAwareRiskModel):
                model.on_position_opened(ctx, symbol)

    def on_position_closed(
        self,
        ctx: AlgorithmContext,
        symbol: str,
        pnl: float,
    ) -> None:
        """Forward to every child that satisfies ``LifecycleAwareRiskModel``."""
        for model in self._models:
            if isinstance(model, LifecycleAwareRiskModel):
                model.on_position_closed(ctx, symbol, pnl)
