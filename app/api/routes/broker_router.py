from fastapi import APIRouter
from pydantic import BaseModel
from app.api.controller.broker import (
    get_alpaca_account_controller,
    get_alpaca_positions_controller,
    add_broker_portfolio_controller,
)

router = APIRouter()

class SyncBrokerPortfolioRequest(BaseModel):
    portfolioName: str
    email: str = "michaellaret7@gmail.com"
    companyName: str = "ProphitAI"

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
async def sync_broker_portfolio(body: SyncBrokerPortfolioRequest):
    """
    Sync Alpaca broker positions to the portfolios table.

    Fetches current positions from Alpaca, calculates percentage allocations
    based on market value, enriches with market data (sector/industry), and
    saves to the user's portfolio database.

    Args:
        body: Request containing portfolioName, email (optional), and companyName (optional)

    Returns:
        Success response with portfolio details including positions synced and allocations
    """
    return await add_broker_portfolio_controller(
        portfolio_name=body.portfolioName,
        email=body.email,
        company_name=body.companyName,
    )
