"""Broker integrations for order execution."""

from prophitai_algo_trading.broker.models import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStartupSnapshot,
    HydrationSummary,
)

__all__: list[str] = [
    "BrokerOrderSnapshot",
    "BrokerPositionSnapshot",
    "BrokerStartupSnapshot",
    "HydrationSummary",
]

try:
    from prophitai_algo_trading.broker.alpaca import Alpaca
except ModuleNotFoundError:
    Alpaca = None  # type: ignore[assignment]
else:
    __all__.append("Alpaca")
