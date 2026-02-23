"""Broker API routes — account, funding, trading, and portfolio history."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from typing import Optional
from app.api.auth.clerk import get_clerk_user_id
from app.api.controller.broker import (
    # Account
    get_broker_account_controller,
    get_buying_power_controller,
    get_cash_balance_controller,
    get_equity_controller,
    get_account_activities_controller,
    create_broker_account_controller,
    # Funding — ACH
    link_bank_account_controller,
    get_ach_relationships_controller,
    delete_ach_relationship_controller,
    # Funding — Transfers
    deposit_controller,
    withdraw_controller,
    get_transfers_controller,
    cancel_transfer_controller,
    instant_deposit_controller,
    # Trading — Orders
    buy_controller,
    sell_controller,
    get_orders_controller,
    get_order_by_id_controller,
    cancel_order_controller,
    cancel_all_orders_controller,
    # Trading — Positions
    get_positions_controller,
    get_position_controller,
    close_position_controller,
    close_all_positions_controller,
    # Portfolio
    get_portfolio_history_controller,
)

router = APIRouter(prefix="/broker", tags=["Broker"])


# ════════════════════════════════════════════════════════════
# --> Request Models
# ════════════════════════════════════════════════════════════

class CreateBrokerAccountRequest(BaseModel):
    """KYC onboarding data."""
    firstName: str
    lastName: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    zip: str
    dob: str
    ssn: str
    fundingSource: str = "employment_income"


class LinkBankRequest(BaseModel):
    """Bank account linking via ACH."""
    accountOwnerName: str
    accountNumber: str
    routingNumber: str
    accountType: str = "checking"


class TransferRequest(BaseModel):
    """Deposit or withdrawal request."""
    relationshipId: str
    amount: float = Field(..., gt=0)


class InstantTransferRequest(BaseModel):
    """Instant deposit from firm funding account."""
    amount: float = Field(..., gt=0)


class OrderRequest(BaseModel):
    """Buy or sell order."""
    symbol: str
    qty: Optional[float] = None
    notional: Optional[float] = None
    limitPrice: Optional[float] = None
    stopPrice: Optional[float] = None
    trailPrice: Optional[float] = None
    trailPercent: Optional[float] = None
    takeProfit: Optional[float] = None
    stopLoss: Optional[float] = None
    stopLossLimit: Optional[float] = None
    orderClass: Optional[str] = None
    timeInForce: str = "day"

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


@router.post("/account", status_code=201)
async def create_broker_account(
    body: CreateBrokerAccountRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Create a brokerage account (KYC onboarding)."""
    return await create_broker_account_controller(
        clerk_id=clerk_id,
        signup_data={
            "first_name": body.firstName,
            "last_name": body.lastName,
            "email": body.email,
            "phone": body.phone,
            "address": body.address,
            "city": body.city,
            "state": body.state,
            "zip": body.zip,
            "dob": body.dob,
            "ssn": body.ssn,
            "funding_source": body.fundingSource,
        },
    )


@router.get("/account/buying-power")
async def get_buying_power(clerk_id: str = Depends(get_clerk_user_id)):
    """Get account buying power."""
    return await get_buying_power_controller(clerk_id=clerk_id)


@router.get("/account/cash")
async def get_cash_balance(clerk_id: str = Depends(get_clerk_user_id)):
    """Get account cash balance."""
    return await get_cash_balance_controller(clerk_id=clerk_id)


@router.get("/account/equity")
async def get_equity(clerk_id: str = Depends(get_clerk_user_id)):
    """Get account equity."""
    return await get_equity_controller(clerk_id=clerk_id)


@router.get("/account/activities")
async def get_account_activities(
    activityType: Optional[str] = Query(None),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get account activities (fills, dividends, transfers, etc.)."""
    return await get_account_activities_controller(
        clerk_id=clerk_id, activity_type=activityType,
    )


# ════════════════════════════════════════════════════════════
# --> Funding — ACH
# ════════════════════════════════════════════════════════════

@router.post("/ach", status_code=201)
async def link_bank_account(
    body: LinkBankRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Link a bank account via ACH."""
    return await link_bank_account_controller(
        clerk_id=clerk_id,
        bank_data={
            "account_owner_name": body.accountOwnerName,
            "account_number": body.accountNumber,
            "routing_number": body.routingNumber,
            "account_type": body.accountType,
        },
    )


@router.get("/ach")
async def get_ach_relationships(clerk_id: str = Depends(get_clerk_user_id)):
    """Get all linked bank accounts."""
    return await get_ach_relationships_controller(clerk_id=clerk_id)


@router.delete("/ach/{relationshipId}")
async def delete_ach_relationship(
    relationshipId: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Remove a bank connection."""
    return await delete_ach_relationship_controller(
        clerk_id=clerk_id, relationship_id=relationshipId,
    )


# ════════════════════════════════════════════════════════════
# --> Funding — Transfers
# ════════════════════════════════════════════════════════════

@router.post("/transfers/deposit", status_code=201)
async def deposit_funds(
    body: TransferRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Deposit money from linked bank into brokerage account."""
    return await deposit_controller(
        clerk_id=clerk_id,
        relationship_id=body.relationshipId,
        amount=body.amount,
    )


@router.post("/transfers/withdraw", status_code=201)
async def withdraw_funds(
    body: TransferRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Withdraw money from brokerage account to linked bank."""
    return await withdraw_controller(
        clerk_id=clerk_id,
        relationship_id=body.relationshipId,
        amount=body.amount,
    )


@router.post("/transfers/instant-deposit", status_code=201)
async def instant_deposit(
    body: InstantTransferRequest,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Instantly journal cash from the firm funding account to the user."""
    return await instant_deposit_controller(
        clerk_id=clerk_id, amount=body.amount,
    )


@router.get("/transfers")
async def get_transfers(clerk_id: str = Depends(get_clerk_user_id)):
    """Get all transfers."""
    return await get_transfers_controller(clerk_id=clerk_id)


@router.delete("/transfers/{transferId}")
async def cancel_transfer(
    transferId: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Cancel a pending transfer."""
    return await cancel_transfer_controller(
        clerk_id=clerk_id, transfer_id=transferId,
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
        limit_price=body.limitPrice,
        stop_price=body.stopPrice,
        trail_price=body.trailPrice,
        trail_percent=body.trailPercent,
        take_profit=body.takeProfit,
        stop_loss=body.stopLoss,
        stop_loss_limit=body.stopLossLimit,
        order_class=body.orderClass,
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
        limit_price=body.limitPrice,
        stop_price=body.stopPrice,
        trail_price=body.trailPrice,
        trail_percent=body.trailPercent,
        take_profit=body.takeProfit,
        stop_loss=body.stopLoss,
        stop_loss_limit=body.stopLossLimit,
        order_class=body.orderClass,
        time_in_force=body.timeInForce,
    )


@router.get("/orders")
async def get_orders(
    status: str = Query("open"),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get orders filtered by status."""
    return await get_orders_controller(clerk_id=clerk_id, status=status)


@router.get("/orders/{orderId}")
async def get_order(
    orderId: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get a specific order by UUID."""
    return await get_order_by_id_controller(
        clerk_id=clerk_id, order_id=orderId,
    )


@router.delete("/orders/{orderId}")
async def cancel_order(
    orderId: str,
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Cancel a specific order."""
    return await cancel_order_controller(
        clerk_id=clerk_id, order_id=orderId,
    )


@router.delete("/orders")
async def cancel_all_orders(clerk_id: str = Depends(get_clerk_user_id)):
    """Cancel all open orders."""
    return await cancel_all_orders_controller(clerk_id=clerk_id)


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


@router.delete("/positions")
async def close_all_positions(
    cancelOrders: bool = Query(True),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Close all positions."""
    return await close_all_positions_controller(
        clerk_id=clerk_id, cancel_orders=cancelOrders,
    )


# ════════════════════════════════════════════════════════════
# --> Portfolio
# ════════════════════════════════════════════════════════════

@router.get("/portfolio/history")
async def get_portfolio_history(
    period: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    extendedHours: Optional[bool] = Query(None),
    clerk_id: str = Depends(get_clerk_user_id),
):
    """Get historical portfolio equity and P&L over time."""
    return await get_portfolio_history_controller(
        clerk_id=clerk_id, period=period,
        timeframe=timeframe, extended_hours=extendedHours,
    )
