"""User trading repository — order execution and position management."""

from typing import Optional, List, Dict
from app.repositories.user.broker import get_broker, resolve_broker_account


# ════════════════════════════════════════════════════════════
# --> Orders
# ════════════════════════════════════════════════════════════

def buy(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
    order_class: Optional[str] = None,
    time_in_force: str = "day",
) -> Dict:
    """Buy an asset. Order type inferred from parameters."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().buy(
        account_id=account_id, symbol=symbol, qty=qty, notional=notional,
        limit_price=limit_price, stop_price=stop_price,
        trail_price=trail_price, trail_percent=trail_percent,
        take_profit=take_profit, stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit, order_class=order_class,
        time_in_force=time_in_force,
    )


def sell(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    trail_price: Optional[float] = None,
    trail_percent: Optional[float] = None,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None,
    stop_loss_limit: Optional[float] = None,
    order_class: Optional[str] = None,
    time_in_force: str = "day",
) -> Dict:
    """Sell an asset. Order type inferred from parameters."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().sell(
        account_id=account_id, symbol=symbol, qty=qty, notional=notional,
        limit_price=limit_price, stop_price=stop_price,
        trail_price=trail_price, trail_percent=trail_percent,
        take_profit=take_profit, stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit, order_class=order_class,
        time_in_force=time_in_force,
    )


def get_orders(clerk_id: str, status: str = "open") -> List[Dict]:
    """Get orders for a user, filtered by status."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_orders(account_id, status)


def get_order_by_id(clerk_id: str, order_id: str) -> Dict:
    """Get a specific order by UUID."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_order_by_id(account_id, order_id)


def cancel_order(clerk_id: str, order_id: str) -> None:
    """Cancel a specific order."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    get_broker().cancel_order(account_id, order_id)


def cancel_all_orders(clerk_id: str) -> None:
    """Cancel all open orders for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    get_broker().cancel_all_orders(account_id)


# ════════════════════════════════════════════════════════════
# --> Positions
# ════════════════════════════════════════════════════════════

def get_positions(clerk_id: str) -> List[Dict]:
    """Get all positions for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_positions(account_id)


def get_position(clerk_id: str, symbol: str) -> Optional[Dict]:
    """Get position for a specific symbol."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_position(account_id, symbol)


def close_position(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> Dict:
    """Close a position fully or partially."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().close_position(account_id, symbol, qty=qty, percentage=percentage)


def close_all_positions(clerk_id: str, cancel_orders: bool = True) -> List[Dict]:
    """Close all positions for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().close_all_positions(account_id, cancel_orders)
