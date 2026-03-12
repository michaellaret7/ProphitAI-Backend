"""Broker API routes — account, trading, and portfolio history via SnapTrade."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, model_validator
from typing import Optional
from app.api.auth.clerk import get_clerk_user_id
from app.api.controller.broker import (
    # Account
    get_broker_account_controller,
    get_balances_controller,
    get_connection_status_controller,
    snaptrade_register_controller,
    snaptrade_callback_controller,
    snaptrade_connect_controller,
    # Connection Management
    list_connections_controller,
    remove_connection_controller,
    # Trading — Orders
    buy_controller,
    sell_controller,
    get_orders_controller,
    cancel_order_controller,
    # Trading — Positions
    get_positions_controller,
    get_position_controller,
    close_position_controller,
    # Portfolio
    get_portfolio_history_controller,
)

router = APIRouter(prefix="/broker", tags=["Broker"])


# ════════════════════════════════════════════════════════════
# --> Request Models
# ════════════════════════════════════════════════════════════

class SnapTradeConnectRequest(BaseModel):
    """Optional params for SnapTrade connection portal redirect."""
    broker: Optional[str] = None
    customRedirect: Optional[str] = None


class OrderRequest(BaseModel):
    """Buy or sell order via SnapTrade."""
    symbol: str
    qty: Optional[float] = None
    notional: Optional[float] = None
    orderType: str = "Market"
    limitPrice: Optional[float] = None
    stopPrice: Optional[float] = None
    timeInForce: str = "Day"

    @model_validator(mode="after")
    def validate_qty_or_notional(self):
        if self.qty is None and self.notional is None:
            raise ValueError("Either qty or notional is required")
        if self.qty is not None and self.notional is not None:
            raise ValueError("Cannot specify both qty and notional")
        return self


# ════════════════════════════════════════════════════════════
# --> Connection Status
# ════════════════════════════════════════════════════════════

@router.get("/connection-status")
async def get_connection_status(clerk_id: str = Depends(get_clerk_user_id)):
    """Check whether the user has a connected brokerage account."""
    return await get_connection_status_controller(clerk_id=clerk_id)


# ════════════════════════════════════════════════════════════
# --> Connection Management
# ════════════════════════════════════════════════════════════

@router.get("/connections")
async def list_connections(clerk_id: str = Depends(get_clerk_user_id)):
    """List all SnapTrade brokerage connections."""
    return await list_connections_controller(clerk_id=clerk_id)


@router.delete("/connections/{authorization_id}")
async def delete_connection(
    authorization_id: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Delete a SnapTrade brokerage connection."""
    return await remove_connection_controller(
        clerk_id=clerk_id,
        authorization_id=authorization_id,
    )


# ════════════════════════════════════════════════════════════
# --> SnapTrade Registration & Callback
# ════════════════════════════════════════════════════════════

@router.post("/snaptrade/register")
async def snaptrade_register(clerk_id: str = Depends(get_clerk_user_id)):
    """Register a new user with SnapTrade."""
    return await snaptrade_register_controller(clerk_id=clerk_id)


@router.post("/snaptrade/callback")
async def snaptrade_callback(clerk_id: str = Depends(get_clerk_user_id)):
    """Save SnapTrade account after OAuth completion."""
    return await snaptrade_callback_controller(clerk_id=clerk_id)


# ════════════════════════════════════════════════════════════
# --> Account Info
# ════════════════════════════════════════════════════════════

@router.get("/account")
async def get_broker_account(clerk_id: str = Depends(get_clerk_user_id)):
    """Get full broker account info."""
    return await get_broker_account_controller(clerk_id=clerk_id)


@router.post("/snaptrade/connect")
async def snaptrade_connect(
    body: SnapTradeConnectRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Generate a SnapTrade connection portal redirect URL."""
    return await snaptrade_connect_controller(
        clerk_id=clerk_id,
        broker=body.broker,
        custom_redirect=body.customRedirect,
    )


@router.get("/account/balances")
async def get_balances(clerk_id: str = Depends(get_clerk_user_id)):
    """Get account balances (cash, buying power, equity)."""
    return await get_balances_controller(clerk_id=clerk_id)


# ════════════════════════════════════════════════════════════
# --> Trading — Orders
# ════════════════════════════════════════════════════════════

@router.post("/orders/buy", status_code=201)
async def buy_order(
    body: OrderRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Place a buy order."""
    return await buy_controller(
        clerk_id=clerk_id,
        symbol=body.symbol,
        qty=body.qty,
        notional=body.notional,
        order_type=body.orderType,
        limit_price=body.limitPrice,
        stop_price=body.stopPrice,
        time_in_force=body.timeInForce,
    )


@router.post("/orders/sell", status_code=201)
async def sell_order(
    body: OrderRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Place a sell order."""
    return await sell_controller(
        clerk_id=clerk_id,
        symbol=body.symbol,
        qty=body.qty,
        notional=body.notional,
        order_type=body.orderType,
        limit_price=body.limitPrice,
        stop_price=body.stopPrice,
        time_in_force=body.timeInForce,
    )


@router.get("/orders")
async def get_orders(
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get recent BUY/SELL trade activity."""
    return await get_orders_controller(
        clerk_id=clerk_id, start_date=startDate, end_date=endDate,
    )


@router.delete("/orders/{orderId}")
async def cancel_order(
    orderId: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Cancel a specific order."""
    return await cancel_order_controller(
        clerk_id=clerk_id, brokerage_order_id=orderId,
    )


# ════════════════════════════════════════════════════════════
# --> Trading — Positions
# ════════════════════════════════════════════════════════════

@router.get("/positions")
async def get_positions(clerk_id: str = Depends(get_clerk_user_id)):
    """Get all positions."""
    return await get_positions_controller(clerk_id=clerk_id)


@router.get("/positions/{symbol}")
async def get_position(
    symbol: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get position for a specific symbol."""
    return await get_position_controller(
        clerk_id=clerk_id, symbol=symbol,
    )


@router.delete("/positions/{symbol}")
async def close_position(
    symbol: str,
    qty: Optional[float] = Query(None),
    percentage: Optional[float] = Query(None),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Close a position fully or partially."""
    return await close_position_controller(
        clerk_id=clerk_id, symbol=symbol,
        qty=qty, percentage=percentage,
    )


# ════════════════════════════════════════════════════════════
# --> Portfolio
# ════════════════════════════════════════════════════════════

@router.get("/portfolio/history")
async def get_portfolio_history(
    years: int = Query(2, description="Years of historical data", ge=1, le=10),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get historical portfolio performance report."""
    return await get_portfolio_history_controller(
        clerk_id=clerk_id,
        years=years,
    )
