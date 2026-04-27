"""``BarRunner`` — the shared per-bar pipeline for all engines.

One class, one public method — ``step(ctx)`` — that runs the full
alpha → PCM → risk.manage → execution → lifecycle sequence for a single
``AlgorithmContext``. Every engine (backtest, live) wraps ``BarRunner``
and owns only the bar-acquisition concern (historical slicing vs.
streaming batching). The duplicated per-bar pipeline and position-diff
logic that used to live in ``EventDrivenBacktest`` and ``LiveRunner``
now lives here once.

``force_flatten(ctx)`` handles end-of-backtest cleanup. It emits
zero-share targets through the same ``ExecutionModel`` + lifecycle path
as any normal bar, so every closed position generates a ``Trade``
record AND a lifecycle event — consistent with regular execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.engines.lifecycle import (
    emit_lifecycle,
    snapshot_positions,
)
from prophitai_algo_trading.core.models import PortfolioTarget

if TYPE_CHECKING:
    from prophitai_algo_trading.core.algorithm import Algorithm
    from prophitai_algo_trading.core.models import AlgorithmContext


#     ================================
# --> Runner
#     ================================

class BarRunner:
    """Runs one ``Algorithm`` pipeline step per ``AlgorithmContext``.

    Args:
        algorithm: Fully-configured ``Algorithm`` (alphas + PCM + risk +
            execution). The same ``Algorithm`` instance backs both
            backtest and live — only the ``ExecutionModel``'s sink
            differs.
    """

    def __init__(self, algorithm: "Algorithm"):
        self.algorithm = algorithm

    def step(self, ctx: "AlgorithmContext") -> None:
        """Run the full pipeline for one bar.

        Sequence:
            1. Alphas → list[Insight] (concatenated across alphas).
            2. PortfolioConstructionModel → list[PortfolioTarget].
            3. RiskManagementModel.manage → list[PortfolioTarget].
            4. Snapshot positions + trade count pre-execute.
            5. ExecutionModel.execute (mutates ctx.portfolio via sink).
            6. Lifecycle emission to the risk model if it structurally
               satisfies ``LifecycleAwareRiskModel``.
        """
        insights: list = []

        for alpha in self.algorithm.alphas:
            insights.extend(alpha.update(ctx))

        targets = self.algorithm.portfolio_construction.create_targets(
            ctx, insights,
        )
        targets = self.algorithm.risk_management.manage(ctx, targets)

        before = snapshot_positions(ctx.portfolio)
        trades_before = len(ctx.portfolio.trades)

        self.algorithm.execution.execute(ctx, targets)

        emit_lifecycle(
            self.algorithm.risk_management, ctx, before, trades_before,
        )

    def force_flatten(self, ctx: "AlgorithmContext") -> None:
        """Close every open position through the normal execution path.

        Used at the end of a backtest so final trades land in the trade
        log with lifecycle events fired. Bypasses alphas + PCM + risk
        gates — this is an unconditional wind-down, not a normal bar.
        """
        open_symbols = list(ctx.portfolio.positions.keys())

        if not open_symbols:
            return

        targets = [
            PortfolioTarget(
                symbol=symbol, target_shares=0.0, exit_reason="engine_eod",
            )
            for symbol in open_symbols
        ]

        before = snapshot_positions(ctx.portfolio)
        trades_before = len(ctx.portfolio.trades)

        self.algorithm.execution.execute(ctx, targets)

        emit_lifecycle(
            self.algorithm.risk_management, ctx, before, trades_before,
        )
