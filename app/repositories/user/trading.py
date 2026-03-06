"""User trading repository — order execution and position management via SnapTrade."""

from typing import Optional, List, Dict
from app.repositories.user.broker import get_snaptrade_broker, resolve_snaptrade_credentials


# ════════════════════════════════════════════════════════════
# --> Orders
# ════════════════════════════════════════════════════════════

def buy(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
) -> Dict:
    """
    Buy an asset via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID
        symbol: Ticker symbol
        qty: Number of shares/units
        notional: Dollar amount to buy
        order_type: Order type (Market, Limit, StopLimit, StopLoss)
        limit_price: Limit price for Limit/StopLimit orders
        stop_price: Stop price for StopLimit/StopLoss orders
        time_in_force: Time in force (Day, GTC)

    Returns:
        Order result dict from SnapTrade
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()

    kwargs = {
        "user_id": creds["snaptrade_user_id"],
        "user_secret": creds["snaptrade_user_secret"],
        "account_id": creds["snaptrade_account_id"],
        "symbol": symbol,
        "order_type": order_type,
        "time_in_force": time_in_force,
    }
    if qty is not None:
        kwargs["units"] = qty
    if notional is not None:
        kwargs["notional"] = notional
    if limit_price is not None:
        kwargs["price"] = limit_price
    if stop_price is not None:
        kwargs["stop"] = stop_price

    return broker.buy(**kwargs)


def sell(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    notional: Optional[float] = None,
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
) -> Dict:
    """
    Sell an asset via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID
        symbol: Ticker symbol
        qty: Number of shares/units
        notional: Dollar amount to sell
        order_type: Order type (Market, Limit, StopLimit, StopLoss)
        limit_price: Limit price for Limit/StopLimit orders
        stop_price: Stop price for StopLimit/StopLoss orders
        time_in_force: Time in force (Day, GTC)

    Returns:
        Order result dict from SnapTrade
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()

    kwargs = {
        "user_id": creds["snaptrade_user_id"],
        "user_secret": creds["snaptrade_user_secret"],
        "account_id": creds["snaptrade_account_id"],
        "symbol": symbol,
        "order_type": order_type,
        "time_in_force": time_in_force,
    }
    if qty is not None:
        kwargs["units"] = qty
    if notional is not None:
        kwargs["notional"] = notional
    if limit_price is not None:
        kwargs["price"] = limit_price
    if stop_price is not None:
        kwargs["stop"] = stop_price

    return broker.sell(**kwargs)


def get_orders(clerk_id: str, state: str = "open") -> List[Dict]:
    """
    Get orders for a user, filtered by state.

    Args:
        clerk_id: Clerk authentication ID
        state: Order state filter (open, executed, cancelled, all)

    Returns:
        List of order dicts
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_orders(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
        state=state,
    )


def cancel_order(clerk_id: str, brokerage_order_id: str) -> Dict:
    """
    Cancel a specific order.

    Args:
        clerk_id: Clerk authentication ID
        brokerage_order_id: Brokerage-assigned order ID

    Returns:
        Cancellation result dict
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.cancel_order(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
        brokerage_order_id=brokerage_order_id,
    )


# ════════════════════════════════════════════════════════════
# --> Positions
# ════════════════════════════════════════════════════════════

def get_positions(clerk_id: str) -> List[Dict]:
    """
    Get all positions for a user via SnapTrade holdings.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        List of position dicts
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    portfolio = broker.get_portfolio(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
    )
    return [p.model_dump() for p in portfolio.equity_positions]


def get_position(clerk_id: str, symbol: str) -> Optional[Dict]:
    """
    Get position for a specific symbol.

    Args:
        clerk_id: Clerk authentication ID
        symbol: Ticker symbol to look up

    Returns:
        Position dict or None if not found
    """
    positions = get_positions(clerk_id=clerk_id)
    symbol_upper = symbol.upper()
    for pos in positions:
        if pos.get("ticker", "").upper() == symbol_upper:
            return pos
    return None


def close_position(
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> Dict:
    """
    Close a position fully or partially by selling units.

    Args:
        clerk_id: Clerk authentication ID
        symbol: Ticker symbol
        qty: Number of units to sell (if partial)
        percentage: Percentage of position to close (0-100)

    Returns:
        Sell order result dict
    """
    if qty is not None:
        units_to_sell = qty
    elif percentage is not None:
        position = get_position(clerk_id=clerk_id, symbol=symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")
        total_units = float(position.get("units", 0))
        units_to_sell = total_units * (percentage / 100.0)
    else:
        # Reason: no qty or percentage means close entire position
        position = get_position(clerk_id=clerk_id, symbol=symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")
        units_to_sell = float(position.get("units", 0))

    return sell(clerk_id=clerk_id, symbol=symbol, qty=units_to_sell)
