"""Order sinks — side-effect adapters for ``ExecutionModel``.

``ExecutionModel`` owns the *decision* (flat/open/close/resize/flip,
material-change filter, warmup suppression). The sink owns the
*side-effect* (mutate portfolio, call broker, mirror broker fill into
portfolio). Two sinks are supplied:

    PortfolioSink
        Pure in-memory. Delegates directly to ``ctx.portfolio.open`` and
        ``ctx.portfolio.close``. Used for backtests.

    BrokerSink
        Routes to a broker (Alpaca-shaped ``buy`` / ``sell`` /
        ``close_position``) and mirrors the fill into ``ctx.portfolio``
        on success. Broker rejections are logged and swallowed per
        symbol — one failed order does not kill the bar. The mirror
        update only lands after the broker call succeeds, so a failed
        order doesn't drift the mirror out of sync.

Both sinks share the same surface so ``ExecutionModel`` is entirely
sink-agnostic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from prophitai_algo_trading.core.models import AlgorithmContext


logger = logging.getLogger(__name__)


#     ================================
# --> Broker protocol
#     ================================

class _BrokerLike(Protocol):
    """Minimum surface ``BrokerSink`` needs from a broker."""

    def buy(self, symbol: str, qty: Any) -> Any: ...
    def sell(self, symbol: str, qty: Any) -> Any: ...
    def close_position(self, symbol: str) -> Any: ...


#     ================================
# --> Sink protocol
#     ================================

@runtime_checkable
class OrderSink(Protocol):
    """Side-effect adapter for ``ExecutionModel`` decisions.

    Two methods, one for each decision outcome. The sink is responsible
    for *all* state changes that follow from the decision — including
    mirror-portfolio updates when the primary side-effect is a broker
    call.
    """

    def open(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        direction: int,
        shares: float,
        price: float,
    ) -> None: ...

    def close(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        price: float,
    ) -> None: ...


#     ================================
# --> Portfolio sink
#     ================================

class PortfolioSink:
    """In-memory sink — mutates ``ctx.portfolio`` directly.

    Used in backtests. ``ExecutionModel`` + ``PortfolioSink`` reproduces
    the old ``SimulatedExecutionModel`` behavior exactly.
    """

    def open(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        direction: int,
        shares: float,
        price: float,
    ) -> None:
        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def close(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        price: float,
    ) -> None:
        ctx.portfolio.close(symbol, price, ctx.timestamp)


#     ================================
# --> Broker sink
#     ================================

class BrokerSink:
    """Broker sink — routes orders through a broker and mirrors the fill.

    The mirror update (``ctx.portfolio.open`` / ``ctx.portfolio.close``)
    only happens after the broker call succeeds, so rejected orders
    don't drift the mirror out of sync with the real brokerage account.

    Args:
        broker: Any object implementing ``buy(symbol, qty)`` /
            ``sell(symbol, qty)`` / ``close_position(symbol)``. Typical
            concrete type: ``prophitai_algo_trading.brokers.alpaca.facade.Alpaca``.
    """

    def __init__(self, broker: _BrokerLike):
        self._broker = broker

    def open(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        direction: int,
        shares: float,
        price: float,
    ) -> None:
        try:
            if direction == 1:
                self._broker.buy(symbol, qty=shares)
            else:
                self._broker.sell(symbol, qty=shares)
        except Exception:
            logger.exception("Broker open failed for %s", symbol)
            return

        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def close(
        self,
        ctx: "AlgorithmContext",
        symbol: str,
        price: float,
    ) -> None:
        try:
            self._broker.close_position(symbol)
        except Exception:
            logger.exception("Broker close failed for %s", symbol)
            return

        ctx.portfolio.close(symbol, price, ctx.timestamp)
