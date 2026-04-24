"""Vendor broker integrations.

Vendor-scoped: each brokerage gets its own subpackage under ``brokers/``
(``alpaca``, and future peers like ``ibkr`` / ``tradestation``). Every
vendor exposes a top-level facade (``Alpaca``, ``IBKR``, …) that the
engines consume through duck-typed calls.

Shared cross-vendor types (startup snapshots, order snapshots) live
here at the top level so engines don't depend on vendor internals.
"""

from prophitai_algo_trading.brokers.alpaca import Alpaca
from prophitai_algo_trading.brokers.snapshots import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStartupSnapshot,
)

__all__ = [
    "Alpaca",
    "BrokerOrderSnapshot",
    "BrokerPositionSnapshot",
    "BrokerStartupSnapshot",
]
