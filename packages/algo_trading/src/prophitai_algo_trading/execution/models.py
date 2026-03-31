"""Shared data types for the execution layer.

Defines enums and dataclasses used by executors, position sizers, and the
execution engine for tracking positions, trades, portfolio context, and
standardized trade candidates for sizing.
"""

from dataclasses import dataclass, field
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
    latest_prices: dict[str, float] = field(default_factory=dict)
    open_position_count: int = 0
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    long_exposure: float = 0.0
    short_exposure: float = 0.0
    peak_equity: float = 0.0
    drawdown_pct: float = 0.0
    timestamp: datetime | None = None


@dataclass
class TradeCandidate:
    """Standardized entry candidate passed from strategies into sizers.

    Strategies can use custom local indicators internally, but they should map
    the final sizing-relevant outputs onto this shared structure so reusable
    sizing policies can work across strategies.
    """

    symbol: str
    direction: Direction
    target_position: int
    price: float
    timestamp: datetime
    score: float
    strategy_id: str
    stop_price: float | None = None
    stop_distance: float | None = None
    risk_per_share: float | None = None
    atr: float | None = None
    volatility: float | None = None
    regime: str | int | None = None
    expected_holding_bars: int | None = None
    liquidity: float | None = None
    raw_features: dict[str, object] = field(default_factory=dict)


@dataclass
class SizingDecision:
    """Sizer output for an entry candidate."""

    shares: float
    target_notional: float | None = None
    risk_budget: float | None = None
    skip_reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
