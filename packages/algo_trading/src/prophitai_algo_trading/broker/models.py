"""Broker startup snapshot models for live engine hydration.

These dataclasses represent the normalized broker state needed to hydrate
the live engine at startup. They are Alpaca-specific in origin but structured
as plain data so the live engine never touches raw Alpaca response dicts.
"""

from dataclasses import dataclass, field
from datetime import datetime

from prophitai_algo_trading.execution.models import Direction


@dataclass
class BrokerPositionSnapshot:
    """A single broker position normalized for engine consumption."""

    symbol: str
    shares: float
    direction: Direction
    entry_price: float
    entry_date: datetime | None = None


@dataclass
class BrokerOrderSnapshot:
    """A single open order normalized for startup validation."""

    order_id: str
    symbol: str
    side: str
    qty: float | None
    status: str
    order_type: str


@dataclass
class BrokerStartupSnapshot:
    """Complete broker state snapshot fetched at live engine startup."""

    cash: float
    equity: float
    positions: list[BrokerPositionSnapshot] = field(default_factory=list)
    open_orders: list[BrokerOrderSnapshot] = field(default_factory=list)
    captured_at: datetime | None = None


@dataclass
class HydrationSummary:
    """Result of startup hydration for logging and diagnostics."""

    cash: float
    equity: float
    hydrated_count: int
    hydrated_symbols: list[str]
    unmanaged_symbols: list[str]
    open_order_count: int
    success: bool
