"""Broker trading controllers — orders, positions, and portfolio history."""

from typing import Optional, Dict, Any
from app.repositories.user.trading import (
    buy,
    sell,
    get_orders,
    get_order_by_id,
    cancel_order,
    cancel_all_orders,
    get_positions,
    get_position,
    close_position,
    close_all_positions,
)
from app.repositories.user.portfolio import get_portfolio_history
from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _order_controller(
    clerk_id: str,
    side_fn,
    symbol: str,
    qty: Optional[float],
    notional: Optional[float],
    limit_price: Optional[float],
    stop_price: Optional[float],
    trail_price: Optional[float],
    trail_percent: Optional[float],
    take_profit: Optional[float],
    stop_loss: Optional[float],
    stop_loss_limit: Optional[float],
    order_class: Optional[str],
    time_in_force: str,
) -> Dict:
    """Shared logic for buy/sell controllers."""
    return side_fn(
        clerk_id=clerk_id,
        symbol=symbol,
        qty=qty,
        notional=notional,
        limit_price=limit_price,
        stop_price=stop_price,
        trail_price=trail_price,
        trail_percent=trail_percent,
        take_profit=take_profit,
        stop_loss=stop_loss,
        stop_loss_limit=stop_loss_limit,
        order_class=order_class,
        time_in_force=time_in_force,
    )


# ════════════════════════════════════════════════════════════
# --> Orders
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def buy_controller(
    *,
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
) -> Dict[str, Any]:
    """Place a buy order."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = _order_controller(
        clerk_id, buy, symbol, qty, notional, limit_price, stop_price,
        trail_price, trail_percent, take_profit, stop_loss, stop_loss_limit,
        order_class, time_in_force,
    )

    return ok_envelope(
        message="Buy order placed successfully",
        kind="broker#order",
        self_link="/api/broker/orders",
        status=201,
        payload=result,
    )


@handle_controller_errors
async def sell_controller(
    *,
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
) -> Dict[str, Any]:
    """Place a sell order."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = _order_controller(
        clerk_id, sell, symbol, qty, notional, limit_price, stop_price,
        trail_price, trail_percent, take_profit, stop_loss, stop_loss_limit,
        order_class, time_in_force,
    )

    return ok_envelope(
        message="Sell order placed successfully",
        kind="broker#order",
        self_link="/api/broker/orders",
        status=201,
        payload=result,
    )


@handle_controller_errors
async def get_orders_controller(
    *, clerk_id: str, status: str = "open"
) -> Dict[str, Any]:
    """Get orders for a user, filtered by status."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    orders = get_orders(clerk_id=clerk_id, status=status)

    return ok_envelope(
        message="Orders retrieved successfully",
        kind="broker#orders",
        self_link="/api/broker/orders",
        counts={"totalItems": len(orders)},
        payload=orders,
    )


@handle_controller_errors
async def get_order_by_id_controller(
    *, clerk_id: str, order_id: str
) -> Dict[str, Any]:
    """Get a specific order by UUID."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not order_id:
        raise ValueError("orderId is required")

    order = get_order_by_id(clerk_id=clerk_id, order_id=order_id)

    return ok_envelope(
        message="Order retrieved successfully",
        kind="broker#order",
        resource_id=order_id,
        self_link=f"/api/broker/orders/{order_id}",
        payload=order,
    )


@handle_controller_errors
async def cancel_order_controller(
    *, clerk_id: str, order_id: str
) -> Dict[str, Any]:
    """Cancel a specific order."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not order_id:
        raise ValueError("orderId is required")

    cancel_order(clerk_id=clerk_id, order_id=order_id)

    return ok_envelope(
        message="Order cancelled successfully",
        kind="broker#order",
        resource_id=order_id,
        self_link=f"/api/broker/orders/{order_id}",
        payload={},
    )


@handle_controller_errors
async def cancel_all_orders_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Cancel all open orders for a user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    cancel_all_orders(clerk_id=clerk_id)

    return ok_envelope(
        message="All orders cancelled successfully",
        kind="broker#orders",
        self_link="/api/broker/orders",
        payload={},
    )


# ════════════════════════════════════════════════════════════
# --> Positions
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_positions_controller(*, clerk_id: str) -> Dict[str, Any]:
    """Get all positions for a user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    positions = get_positions(clerk_id=clerk_id)

    return ok_envelope(
        message="Positions retrieved successfully",
        kind="broker#positions",
        self_link="/api/broker/positions",
        counts={"totalItems": len(positions)},
        payload=positions,
    )


@handle_controller_errors
async def get_position_controller(
    *, clerk_id: str, symbol: str
) -> Dict[str, Any]:
    """Get position for a specific symbol."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not symbol:
        raise ValueError("symbol is required")

    position = get_position(clerk_id=clerk_id, symbol=symbol.upper())

    return ok_envelope(
        message="Position retrieved successfully",
        kind="broker#position",
        self_link=f"/api/broker/positions/{symbol.upper()}",
        payload=position,
    )


@handle_controller_errors
async def close_position_controller(
    *,
    clerk_id: str,
    symbol: str,
    qty: Optional[float] = None,
    percentage: Optional[float] = None,
) -> Dict[str, Any]:
    """Close a position fully or partially."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not symbol:
        raise ValueError("symbol is required")

    result = close_position(
        clerk_id=clerk_id, symbol=symbol.upper(),
        qty=qty, percentage=percentage,
    )

    return ok_envelope(
        message="Position closed successfully",
        kind="broker#position",
        self_link=f"/api/broker/positions/{symbol.upper()}",
        payload=result,
    )


@handle_controller_errors
async def close_all_positions_controller(
    *, clerk_id: str, cancel_orders: bool = True
) -> Dict[str, Any]:
    """Close all positions for a user."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    results = close_all_positions(
        clerk_id=clerk_id, cancel_orders=cancel_orders,
    )

    return ok_envelope(
        message="All positions closed successfully",
        kind="broker#positions",
        self_link="/api/broker/positions",
        payload=results,
    )


# ════════════════════════════════════════════════════════════
# --> Portfolio History
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_portfolio_history_controller(
    *,
    clerk_id: str,
    period: Optional[str] = None,
    timeframe: Optional[str] = None,
    extended_hours: Optional[bool] = None,
) -> Dict[str, Any]:
    """Get historical portfolio equity and P&L over time."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    history = get_portfolio_history(
        clerk_id=clerk_id, period=period,
        timeframe=timeframe, extended_hours=extended_hours,
    )

    return ok_envelope(
        message="Portfolio history retrieved successfully",
        kind="broker#portfolioHistory",
        self_link="/api/broker/portfolio/history",
        payload=history,
    )
