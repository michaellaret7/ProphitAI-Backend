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
"""

from __future__ import annotations

from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    PortfolioTarget,
)
from prophitai_algo_trading.framework.protocols import RiskManagementModel


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
    # --> Lifecycle forwarding (engine hooks)
    #     ================================

    def notify_entry(self, ctx: AlgorithmContext, symbol: str) -> None:
        """Forward on_entry to every child that supports it."""
        for model in self._models:
            notifier = getattr(model, "notify_entry", None)

            if notifier is not None:
                notifier(ctx, symbol)

    def notify_exit(
        self,
        ctx: AlgorithmContext,
        symbol: str,
        trade_pnl: float,
    ) -> None:
        """Forward on_exit to every child that supports it."""
        for model in self._models:
            notifier = getattr(model, "notify_exit", None)

            if notifier is not None:
                notifier(ctx, symbol, trade_pnl)
