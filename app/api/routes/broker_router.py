from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.controller.broker import (
    get_alpaca_account_controller,
    get_alpaca_positions_controller,
    add_broker_portfolio_controller,
)
from app.api.auth.clerk import get_clerk_user_id
from app.repositories.user_data import get_all_user_data_by_clerk_id

router = APIRouter(tags=["Broker Support 🏦"])


async def get_user_id_from_clerk(clerk_id: str = Depends(get_clerk_user_id)) -> str:
    """Get internal database user_id from Clerk ID."""
    user_data = get_all_user_data_by_clerk_id(clerk_id=clerk_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data.get("id")


class SyncBrokerPortfolioRequest(BaseModel):
    portfolioName: str

@router.get("/broker/alpaca/account")
async def get_alpaca_account():
    """
    Get Alpaca account information.

    Returns:
        Account details including equity, cash, buying power, and other account metrics
    """
    return await get_alpaca_account_controller()

@router.get("/broker/alpaca/positions")
async def get_alpaca_positions():
    """
    Get all current positions in the Alpaca account.

    Returns:
        List of all open positions with details including ticker, quantity, market value,
        cost basis, and unrealized P&L
    """
    return await get_alpaca_positions_controller()

@router.post("/broker/alpaca/sync-portfolio", status_code=201)
async def sync_broker_portfolio(
    body: SyncBrokerPortfolioRequest,
    user_id: str = Depends(get_user_id_from_clerk),
):
    """
    Sync Alpaca broker positions to the portfolios table.

    Fetches current positions from Alpaca, calculates percentage allocations
    based on market value, enriches with market data (sector/industry), and
    saves to the user's portfolio database.

    Args:
        body: Request containing portfolioName

    Returns:
        Success response with portfolio details including positions synced and allocations
    """
    return await add_broker_portfolio_controller(
        portfolio_name=body.portfolioName,
        user_id=user_id,
    )
