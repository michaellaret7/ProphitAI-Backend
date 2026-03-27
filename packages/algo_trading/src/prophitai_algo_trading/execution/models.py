"""Shared data types for the execution layer.

Defines enums and dataclasses used by executors, position sizers, and the
execution engine for tracking positions, trades, and portfolio context.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Direction(str, Enum):
    """Trade direction for position tracking."""

    LONG = "long"
    SHORT = "short"


@dataclass
class Trade:
    """Record of a completed round-trip trade."""

    symbol: str
    entry_date: datetime
    exit_date: datetime
    direction: Direction
    entry_price: float
    exit_price: float
    shares: float
    pnl: float
    return_pct: float


@dataclass
class PositionState:
    """Snapshot of an open position for a single symbol."""

    symbol: str
    shares: float
    direction: Direction
    entry_price: float
    entry_date: datetime
    entry_commission: float


@dataclass
class PortfolioContext:
    """Portfolio state passed to position sizers for allocation decisions."""

    equity: float
    cash: float
    positions: dict[str, PositionState]
