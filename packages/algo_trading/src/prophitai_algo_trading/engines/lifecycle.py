"""Position lifecycle diffing — stateless helpers for ``BarRunner``.

Two free functions. ``snapshot_positions`` captures the pre-execute
state; ``emit_lifecycle`` diffs it against the post-execute state and
fires ``on_position_opened`` / ``on_position_closed`` on the risk model
if — and only if — the model structurally satisfies
``LifecycleAwareRiskModel``.

Flip detection is the subtle bit. A position that changes sign in one
step (long → short or short → long) must emit *both* a close (for the
old leg) and an open (for the new leg), because the sink closes then
reopens under the hood. The diff logic below handles this case
explicitly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.core.protocols import LifecycleAwareRiskModel

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext
    from prophitai_algo_trading.core.protocols import RiskManagementModel
    from prophitai_algo_trading.portfolio.portfolio import Portfolio


#     ================================
# --> Pre-execute snapshot
#     ================================

def snapshot_positions(portfolio: "Portfolio") -> dict[str, int]:
    """Symbol -> signed direction (+1 long, -1 short). Flat symbols omitted."""
    return {
        symbol: pos.direction
        for symbol, pos in portfolio.positions.items()
    }


#     ================================
# --> Post-execute diff + emit
#     ================================

def emit_lifecycle(
    risk_model: "RiskManagementModel",
    ctx: "AlgorithmContext",
    before: dict[str, int],
    trades_before: int,
) -> None:
    """Fire lifecycle hooks for every open/close/flip this step produced.

    Gated by ``isinstance(risk_model, LifecycleAwareRiskModel)`` — a risk
    model that doesn't implement the hooks simply gets skipped.

    Args:
        risk_model: The ``RiskManagementModel`` to notify.
        ctx: The algorithm context for the bar that just finished.
        before: Pre-execute ``{symbol: signed_direction}`` snapshot.
        trades_before: ``len(portfolio.trades)`` before execution, used
            to isolate trades produced during this step for P&L lookup.
    """
    if not isinstance(risk_model, LifecycleAwareRiskModel):
        return

    after = snapshot_positions(ctx.portfolio)

    new_trades = ctx.portfolio.trades[trades_before:]
    pnl_by_symbol: dict[str, float] = {
        trade.symbol: trade.pnl for trade in new_trades
    }

    for symbol in set(before) | set(after):
        before_dir = before.get(symbol, 0)
        after_dir = after.get(symbol, 0)

        # Reason: a flip registers as BOTH close-then-open — fire both hooks.
        was_flat = before_dir == 0
        is_flat = after_dir == 0
        flipped = (
            not was_flat and not is_flat and before_dir * after_dir < 0
        )

        closed = not was_flat and (is_flat or flipped)
        opened = not is_flat and (was_flat or flipped)

        if closed:
            risk_model.on_position_closed(
                ctx, symbol, pnl_by_symbol.get(symbol, 0.0),
            )

        if opened:
            risk_model.on_position_opened(ctx, symbol)
