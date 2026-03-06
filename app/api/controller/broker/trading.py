"""Broker trading controllers — orders, positions, and portfolio history."""

from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.repositories.user.trading import (
    buy,
    sell,
    get_orders,
    cancel_order,
    get_positions,
    get_position,
    close_position,
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
    order_type: str,
    limit_price: Optional[float],
    stop_price: Optional[float],
    time_in_force: str,
) -> Dict:
    """Shared logic for buy/sell controllers."""
    return side_fn(
        clerk_id=clerk_id,
        symbol=symbol,
        qty=qty,
        notional=notional,
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
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
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
) -> Dict[str, Any]:
    """Place a buy order."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = _order_controller(
        clerk_id, buy, symbol, qty, notional, order_type,
        limit_price, stop_price, time_in_force,
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
    order_type: str = "Market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    time_in_force: str = "Day",
) -> Dict[str, Any]:
    """Place a sell order."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    result = _order_controller(
        clerk_id, sell, symbol, qty, notional, order_type,
        limit_price, stop_price, time_in_force,
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
    *, clerk_id: str, state: str = "open"
) -> Dict[str, Any]:
    """Get orders for a user, filtered by state."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    orders = get_orders(clerk_id=clerk_id, state=state)

    return ok_envelope(
        message="Orders retrieved successfully",
        kind="broker#orders",
        self_link="/api/broker/orders",
        counts={"totalItems": len(orders)},
        payload=orders,
    )


@handle_controller_errors
async def cancel_order_controller(
    *, clerk_id: str, brokerage_order_id: str
) -> Dict[str, Any]:
    """Cancel a specific order."""
    if not clerk_id:
        raise ValueError("clerkId is required")
    if not brokerage_order_id:
        raise ValueError("brokerageOrderId is required")

    result = cancel_order(clerk_id=clerk_id, brokerage_order_id=brokerage_order_id)

    return ok_envelope(
        message="Order cancelled successfully",
        kind="broker#order",
        resource_id=brokerage_order_id,
        self_link=f"/api/broker/orders/{brokerage_order_id}",
        payload=result,
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

    if position is None:
        raise HTTPException(
            status_code=404,
            detail=f"No position found for {symbol.upper()}",
        )

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


# ════════════════════════════════════════════════════════════
# --> Portfolio History
# ════════════════════════════════════════════════════════════

@handle_controller_errors
async def get_portfolio_history_controller(
    *,
    clerk_id: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Get historical portfolio performance report."""
    if not clerk_id:
        raise ValueError("clerkId is required")

    history = get_portfolio_history(
        clerk_id=clerk_id,
        start_date=start_date,
        end_date=end_date,
    )

    return ok_envelope(
        message="Portfolio history retrieved successfully",
        kind="broker#portfolioHistory",
        self_link="/api/broker/portfolio/history",
        payload=history,
    )
