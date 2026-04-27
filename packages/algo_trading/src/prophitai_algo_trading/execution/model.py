"""Deep ``ExecutionModel`` — decides, then delegates to an ``OrderSink``.

One class, one ``execute()`` method, one shared decision matrix. Where
``SimulatedExecutionModel`` and ``BrokerExecutionModel`` used to
re-implement identical flat/open/close/resize/flip logic, the shared
code now lives here once. The sink is the only thing that differs.

Decision matrix per target:

    target 0, no position       -> no-op
    target 0, position held     -> sink.close()
    target != 0, no position    -> sink.open(direction, |shares|)
    target != 0, same dir held  -> if |delta| material: sink.close + sink.open
                                   else: no-op
    target != 0, opposite dir   -> sink.close + sink.open (flip)

Fills happen at the current bar's close. A future ``fill_price=
"next_open"`` mode would push fills to the next bar's open to eliminate
close-of-bar lookahead; not implemented yet because daily-frequency
strategies don't need it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    PortfolioTarget,
)

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.sinks import OrderSink
    from prophitai_algo_trading.portfolio.portfolio import Portfolio


#     ================================
# --> Helper funcs
#     ================================

def _get_fill_price(ctx: AlgorithmContext, symbol: str) -> float | None:
    """Last-close price for ``symbol`` at the current bar, or None if
    the symbol has no data or a non-positive price."""
    df = ctx.data.get(symbol)

    if df is None or df.empty:
        return None

    price = float(df["close"].iloc[-1])

    if price <= 0.0:
        return None

    return price


def _current_signed_shares(portfolio: "Portfolio", symbol: str) -> float:
    """Return +shares (long), -shares (short), or 0 (flat) for ``symbol``."""
    pos = portfolio.positions.get(symbol)

    if pos is None:
        return 0.0

    return pos.shares * pos.direction


def _is_material_change(
    target_shares: float,
    current_signed: float,
    price: float,
    equity: float,
    min_change_pct: float,
) -> bool:
    """True if the |notional delta| exceeds ``min_change_pct * equity``.

    Used to skip trivial rebalance churn — e.g. "100 shares held, target
    101 shares" is not worth a commission. Notional-based so the
    threshold scales with position size rather than raw share count.
    """
    if equity <= 0 or min_change_pct <= 0:
        return True

    delta_shares = abs(target_shares - current_signed)
    delta_notional = delta_shares * price

    return delta_notional > equity * min_change_pct


#     ================================
# --> Execution model
#     ================================

class ExecutionModel:
    """Deep ``ExecutionModel`` parameterized by an ``OrderSink``.

    Args:
        sink: The side-effect adapter. ``PortfolioSink()`` for backtest,
            ``BrokerSink(broker)`` for live trading.
        min_change_pct: Fraction of equity below which a rebalance is
            skipped. Default 0.005 = 0.5% notional delta.
    """

    def __init__(self, sink: "OrderSink", min_change_pct: float = 0.005):
        if min_change_pct < 0:
            raise ValueError("min_change_pct must be >= 0")

        self._sink = sink
        self._min_change_pct = min_change_pct

    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None:
        if ctx.warmup:
            return

        for target in targets:
            price = _get_fill_price(ctx, target.symbol)

            if price is None:
                continue

            current = _current_signed_shares(ctx.portfolio, target.symbol)

            # Reason: target_shares == 0 always means "flatten the symbol."
            if target.target_shares == 0.0:
                if current != 0.0:
                    self._sink.close(
                        ctx, target.symbol, price,
                        exit_reason=target.exit_reason,
                    )

                continue

            # Reason: empty-to-held opens cleanly through the sink.
            if current == 0.0:
                self._open(ctx, target, price)

                continue

            equity = ctx.portfolio.equity()

            if not _is_material_change(
                target.target_shares, current, price, equity, self._min_change_pct,
            ):
                continue

            # Reason: neither Portfolio nor the broker has a resize
            # primitive — close + reopen is the only way to both
            # crystallize prior P&L and land on the exact new share
            # count. Also cleanly handles flips (opposite direction)
            # since close + reopen doesn't care about the sign of the
            # previous position. Implicit-close attribution: an
            # opposite-sign target is a true direction flip
            # (``alpha_reversal``); a same-sign target is a resize
            # bookkeeping artifact (``resize``). Both are PCM-induced;
            # an explicit ``target.exit_reason`` always wins.
            same_direction = (target.target_shares * current) > 0.0
            close_reason = target.exit_reason or (
                "resize" if same_direction else "alpha_reversal"
            )

            self._sink.close(ctx, target.symbol, price, exit_reason=close_reason)

            self._open(ctx, target, price)

    #     ================================
    # --> Internal
    #     ================================

    def _open(
        self,
        ctx: AlgorithmContext,
        target: PortfolioTarget,
        price: float,
    ) -> None:
        direction = 1 if target.target_shares > 0 else -1
        shares = abs(target.target_shares)

        if shares <= 0:
            return

        self._sink.open(
            ctx, target.symbol, direction, shares, price,
            entry_alphas=target.entry_alphas,
        )
