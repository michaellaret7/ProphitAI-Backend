"""Broker API routes — account, trading, and portfolio history via SnapTrade."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, model_validator
from typing import Optional
from app.api.auth.clerk import get_clerk_user_id
from app.api.controller.broker import (
    # Account
    get_broker_account_controller,
    get_balances_controller,
    get_account_activities_controller,
    snaptrade_connect_controller,
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
    connectionType: Optional[str] = None
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
        connection_type=body.connectionType,
        custom_redirect=body.customRedirect,
    )


@router.get("/account/balances")
async def get_balances(clerk_id: str = Depends(get_clerk_user_id)):
    """Get account balances (cash, buying power, equity)."""
    return await get_balances_controller(clerk_id=clerk_id)


@router.get("/account/activities")
async def get_account_activities(
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    activityType: Optional[str] = Query(None),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get account activities (fills, dividends, transfers, etc.)."""
    return await get_account_activities_controller(
        clerk_id=clerk_id,
        start_date=startDate,
        end_date=endDate,
        activity_type=activityType,
    )


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
    state: str = Query("open"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get orders filtered by state."""
    return await get_orders_controller(clerk_id=clerk_id, state=state)


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
    startDate: str = Query(..., description="Start date (YYYY-MM-DD)"),
    endDate: str = Query(..., description="End date (YYYY-MM-DD)"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get historical portfolio performance report."""
    return await get_portfolio_history_controller(
        clerk_id=clerk_id,
        start_date=startDate,
        end_date=endDate,
    )
