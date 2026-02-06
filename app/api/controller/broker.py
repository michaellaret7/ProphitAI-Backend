import uuid
from app.utils.alpaca.client import AlpacaClient
from app.utils.alpaca.portfolio import AlpacaPortfolio
from app.utils.alpaca.trading import AlpacaTrading
from app.utils.decorators.api_decorators import handle_controller_errors
from app.api.response_envelope import ok_envelope
from app.repositories.portfolio.crud import add_portfolio, delete_portfolio_by_name
from app.services.portfolio.portfolio import Position
from typing import Dict, Any

@handle_controller_errors
async def get_alpaca_account_controller() -> Dict[str, Any]:
    """
    Controller to handle Alpaca account retrieval
    """
    client = AlpacaClient(paper=True)
    portfolio = AlpacaPortfolio(client.get_client())

    return ok_envelope(
        message="Alpaca account retrieved successfully",
        kind="broker#alpacaAccount",
        resource_id="alpaca",
        payload=portfolio.get_account(),
    )

@handle_controller_errors
async def get_alpaca_positions_controller() -> Dict[str, Any]:
    """
    Controller to handle Alpaca positions retrieval
    """
    client = AlpacaClient(paper=True)
    portfolio = AlpacaPortfolio(client.get_client())

    return ok_envelope(
        message="Alpaca positions retrieved successfully",
        kind="broker#alpacaPositions",
        resource_id="alpaca",
        payload=portfolio.get_positions(),
    )


@handle_controller_errors
async def add_broker_portfolio_controller(
    *,
    portfolio_name: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Controller to sync Alpaca broker positions to portfolios table.

    Fetches current positions from Alpaca, calculates allocations based on
    total portfolio market value, enriches with market data, and saves to database.

    Args:
        portfolio_name: Name for the portfolio
        user_id: User's internal database ID

    Returns:
        Response envelope with success message

    Raises:
        ValueError: If no positions found or portfolio creation fails
    """
    # Get Alpaca positions
    client = AlpacaClient(paper=True)
    alpaca_portfolio = AlpacaPortfolio(client.get_client())
    alpaca_positions = alpaca_portfolio.get_positions()

    if not alpaca_positions:
        raise ValueError("No positions found in Alpaca account")

    # Calculate total portfolio value
    total_market_value = sum(pos['market_value'] for pos in alpaca_positions)

    if total_market_value <= 0:
        raise ValueError("Total portfolio market value must be greater than 0")

    # Transform Alpaca positions to Position objects with decimal allocations
    position_objects = []
    for pos in alpaca_positions:
        ticker = pos['symbol']
        market_value = pos['market_value']
        qty = pos.get('qty')  # Number of shares from Alpaca

        # Calculate allocation as decimal (0-1 range, e.g., 0.25 = 25%)
        allocation = market_value / total_market_value

        position_objects.append(Position(
            ticker=ticker,
            allocation=allocation,
            num_shares=int(float(qty)) if qty is not None else None,
            position_nav=market_value
        ))

    # Save to database using existing portfolio repository
    add_portfolio(
        portfolio=position_objects,
        user_id=uuid.UUID(user_id),
        portfolio_name=portfolio_name,
        portfolio_value=total_market_value,
    )

    return ok_envelope(
        message=f"Broker portfolio '{portfolio_name}' synced successfully with {len(position_objects)} positions",
        kind="broker#portfolioSync",
        resource_id=portfolio_name,
        payload={
            "positions_synced": len(position_objects),
            "total_market_value": total_market_value,
            "positions": [
                {
                    "ticker": pos.ticker,
                    "allocation": round(pos.allocation, 2)
                }
                for pos in position_objects
            ]
        }
    )


if __name__ == "__main__":
    import asyncio
    deleted_count = delete_portfolio_by_name(
        portfolio_name="test",
        email="michaellaret7@gmail.com"
    )
    print(f"Deleted {deleted_count} tickers")