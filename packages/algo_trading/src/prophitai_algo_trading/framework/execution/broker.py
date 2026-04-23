"""BrokerExecutionModel — live-side order placement.

Same diffing logic as SimulatedExecutionModel, but each decision routes
through a broker (Alpaca) and the in-memory Portfolio mirrors the
intent so downstream metrics and reporting keep working.

Broker calls that raise are logged and swallowed per-symbol — a single
rejected order should not kill the whole bar. The mirror-portfolio
update only happens after the broker call succeeds, so failed orders
don't drift the mirror out of sync with the real brokerage account.

The broker is duck-typed — anything with ``buy(symbol, qty)``,
``sell(symbol, qty)``, and ``close_position(symbol)`` works. Typical
concrete type: ``prophitai_algo_trading.broker.alpaca.Alpaca``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from prophitai_algo_trading.framework.execution.base import (
    current_signed_shares,
    get_fill_price,
    is_material_change,
)
from prophitai_algo_trading.framework.models import (
    AlgorithmContext,
    PortfolioTarget,
)


logger = logging.getLogger(__name__)


#     ================================
# --> Broker protocol
#     ================================

class _BrokerLike(Protocol):
    """Minimum surface the execution model needs from a broker."""

    def buy(self, symbol: str, qty: Any) -> Any: ...
    def sell(self, symbol: str, qty: Any) -> Any: ...
    def close_position(self, symbol: str) -> Any: ...


#     ================================
# --> Execution model
#     ================================

class BrokerExecutionModel:
    """Live execution against a broker (Alpaca by default).

    Args:
        broker: Any object implementing ``buy/sell/close_position``.
        min_change_pct: Fraction of equity below which a rebalance is
            skipped. Default 0.005 = 0.5% notional delta.
    """

    def __init__(
        self,
        broker: _BrokerLike,
        min_change_pct: float = 0.005,
    ):
        if min_change_pct < 0:
            raise ValueError("min_change_pct must be >= 0")

        self._broker = broker
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

            if target.target_shares == 0.0:
                if current != 0.0:
                    self._close(ctx, target.symbol, price)

                continue

            if current == 0.0:
                self._open(ctx, target.symbol, target.target_shares, price)

                continue

            equity = ctx.portfolio.equity()

            if not is_material_change(
                target.target_shares, current, price, equity, self._min_change_pct,
            ):
                continue

            # Reason: broker has no resize primitive either. Close then
            # reopen, and only update the mirror on each success so a
            # failed reopen doesn't zombify the mirror portfolio.
            self._close(ctx, target.symbol, price)

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

        try:
            if direction == 1:
                self._broker.buy(symbol, qty=shares)
            else:
                self._broker.sell(symbol, qty=shares)
        except Exception:
            logger.exception("Broker open failed for %s", symbol)
            return

        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def _close(
        self,
        ctx: AlgorithmContext,
        symbol: str,
        price: float,
    ) -> None:
        try:
            self._broker.close_position(symbol)
        except Exception:
            logger.exception("Broker close failed for %s", symbol)
            return

        ctx.portfolio.close(symbol, price, ctx.timestamp)
