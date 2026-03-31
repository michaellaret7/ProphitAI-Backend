"""Live startup reconciliation — hydrates engine state from a broker snapshot.

Validates the broker snapshot against the active universe, partitions positions
into managed vs unmanaged, checks for open orders, and seeds the portfolio and
position trackers. This module never fetches data or executes trades — it only
reconciles and applies startup state.
"""

import logging

from prophitai_algo_trading.broker.models import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStartupSnapshot,
    HydrationSummary,
)
from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker

logger = logging.getLogger(__name__)


# ================================
# --> Helper funcs
# ================================

def partition_positions(
    positions: list[BrokerPositionSnapshot],
    active_universe: list[str],
) -> tuple[list[BrokerPositionSnapshot], list[BrokerPositionSnapshot]]:
    """Split broker positions into managed and unmanaged sets.

    Args:
        positions: All positions from the broker snapshot.
        active_universe: Symbols the live engine is configured to trade.

    Returns:
        Tuple of (managed, unmanaged) position lists.
    """
    universe_set = set(active_universe)
    managed = [p for p in positions if p.symbol in universe_set]
    unmanaged = [p for p in positions if p.symbol not in universe_set]
    return managed, unmanaged


def validate_open_orders(
    orders: list[BrokerOrderSnapshot],
    active_universe: list[str],
) -> None:
    """Fail fast if there are open orders for any managed symbols.

    Args:
        orders: Open orders from the broker snapshot.
        active_universe: Symbols the live engine is configured to trade.

    Raises:
        RuntimeError: If any open orders exist for managed symbols.
    """
    universe_set = set(active_universe)
    conflicting = [o for o in orders if o.symbol in universe_set]

    if conflicting:
        symbols = ", ".join(o.symbol for o in conflicting)
        raise RuntimeError(
            f"Cannot start live engine — open orders exist for managed symbols: {symbols}. "
            "Cancel these orders before restarting."
        )


def hydrate_live_state(
    snapshot: BrokerStartupSnapshot,
    portfolio_tracker: PortfolioTracker,
    position_trackers: dict[str, PositionTracker],
    latest_prices: dict[str, float],
    active_universe: list[str],
) -> HydrationSummary:
    """Validate and apply a broker snapshot to the live engine's in-memory state.

    Args:
        snapshot: The startup snapshot fetched from the broker.
        portfolio_tracker: The engine's portfolio tracker (already constructed).
        position_trackers: Per-symbol position trackers keyed by ticker.
        latest_prices: Latest known prices from warmup data.
        active_universe: Symbols the live engine is configured to trade.

    Returns:
        HydrationSummary with diagnostics for logging.

    Raises:
        RuntimeError: On unmanaged positions, open orders for managed symbols,
            or invalid snapshot data.
    """
    managed, unmanaged = partition_positions(snapshot.positions, active_universe)

    # Reason: unmanaged positions mean the broker has positions the engine
    # doesn't know about — unsafe to proceed
    if unmanaged:
        symbols = ", ".join(p.symbol for p in unmanaged)
        raise RuntimeError(
            f"Cannot start live engine — unmanaged broker positions found: {symbols}. "
            "Either add these symbols to the live universe or close them manually."
        )

    validate_open_orders(snapshot.open_orders, active_universe)

    # Reason: seed cash from broker (not equity) so capital already locked
    # in existing positions is not double-counted as free cash
    portfolio_tracker.seed_cash(snapshot.cash)
    portfolio_tracker.seed_latest_prices(latest_prices)

    hydrated_symbols: list[str] = []

    for pos in managed:
        if pos.shares <= 0:
            raise RuntimeError(
                f"Invalid broker position for {pos.symbol}: shares={pos.shares}"
            )

        # Reason: use snapshot capture time as entry_date since the broker
        # does not provide the original fill timestamp
        entry_date = snapshot.captured_at

        portfolio_tracker.seed_position(
            symbol=pos.symbol,
            shares=pos.shares,
            direction=pos.direction,
            entry_price=pos.entry_price,
            entry_date=entry_date,
        )

        # Reason: translate Direction enum to PositionTracker's int convention
        tracker_position = 1 if pos.direction == Direction.LONG else -1
        position_trackers[pos.symbol].hydrate(tracker_position)

        hydrated_symbols.append(pos.symbol)

    return HydrationSummary(
        cash=snapshot.cash,
        equity=snapshot.equity,
        hydrated_count=len(hydrated_symbols),
        hydrated_symbols=hydrated_symbols,
        unmanaged_symbols=[p.symbol for p in unmanaged],
        open_order_count=len(snapshot.open_orders),
        success=True,
    )
