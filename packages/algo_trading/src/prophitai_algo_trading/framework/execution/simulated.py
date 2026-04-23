"""SimulatedExecutionModel — backtest-side order placement.

Diffs current portfolio state against the final target list and routes
the changes through ``Portfolio.open`` / ``Portfolio.close``. No broker
calls, no network — pure Python state mutation against the in-memory
portfolio.

Decision matrix per target:

    target 0, no position       -> no-op
    target 0, position held     -> close()
    target != 0, no position    -> open(direction, |shares|)
    target != 0, same dir held  -> if |delta| material: close + reopen
                                   else: no-op
    target != 0, opposite dir   -> close + reopen (flip)

Fills happen at the current bar's close. A future ``fill_price=
"next_open"`` mode would push fills to the next bar's open to eliminate
close-of-bar lookahead; not implemented yet because daily-frequency
strategies don't need it.
"""

from __future__ import annotations

from prophitai_algo_trading.framework.execution.base import (
    current_signed_shares,
    get_fill_price,
    is_material_change,
)
from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    PortfolioTarget,
)


class SimulatedExecutionModel:
    """In-memory execution against Portfolio.

    Args:
        min_change_pct: Fraction of equity below which a rebalance is
            skipped. Default 0.005 = 0.5% notional delta.
    """

    def __init__(self, min_change_pct: float = 0.005):
        if min_change_pct < 0:
            raise ValueError("min_change_pct must be >= 0")

        self._min_change_pct = min_change_pct

    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None:
        if ctx.warmup:
            return

        for target in targets:
            price = get_fill_price(ctx, target.symbol)

            if price is None:
                continue

            current = current_signed_shares(ctx.portfolio, target.symbol)

            # Reason: target_shares == 0 always means "flatten the symbol."
            if target.target_shares == 0.0:
                if current != 0.0:
                    ctx.portfolio.close(target.symbol, price, ctx.timestamp)

                continue

            # Reason: empty-to-held opens cleanly through portfolio.open.
            if current == 0.0:
                self._open(ctx, target.symbol, target.target_shares, price)

                continue

            equity = ctx.portfolio.equity()

            if not is_material_change(
                target.target_shares, current, price, equity, self._min_change_pct,
            ):
                continue

            # Reason: Portfolio has no resize primitive — close + reopen is
            # the only way to both crystallize prior P&L and land on the
            # exact new share count. Also cleanly handles flips (opposite
            # direction) since close + reopen doesn't care about the sign
            # of the previous position.
            ctx.portfolio.close(target.symbol, price, ctx.timestamp)

            self._open(ctx, target.symbol, target.target_shares, price)

    #     ================================
    # --> Internal
    #     ================================

    def _open(
        self,
        ctx: AlgorithmContext,
        symbol: str,
        target_shares: float,
        price: float,
    ) -> None:
        direction = 1 if target_shares > 0 else -1
        shares = abs(target_shares)

        if shares <= 0:
            return

        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)
