"""User portfolio repository — DB portfolio data and broker portfolio history."""

from typing import Optional, Dict
from app.db.core.models.user_data_models import *
from sqlalchemy.orm import selectinload
from app.utils.decorators.database import with_session
from app.repositories.user.broker import get_broker, resolve_broker_account


@with_session('user')
def get_user_current_portfolio(email: str, session=None):
    """
    Get the current portfolio for a user by email.

    Args:
        email: User's email address

    Returns:
        List of portfolio items for the current portfolio, or None if no current portfolio
    """
    if not email:
        raise ValueError("Email must be provided")

    user = session.query(User).filter(User.email == email).first()

    if not user:
        return None

    # Query through Portfolio table (is_current is on Portfolio, not PortfolioItem)
    current_portfolio = session.query(Portfolio).options(
        selectinload(Portfolio.items)
    ).filter(
        Portfolio.user_id == user.id,
        Portfolio.is_current == True
    ).first()

    if not current_portfolio:
        return None

    # Return portfolio items with nav context
    return [{
        'portfolio_id': str(current_portfolio.id),
        'portfolio_name': current_portfolio.name,
        'nav': current_portfolio.nav,
        'ticker': item.ticker,
        'allocation': item.allocation,
        'num_shares': item.num_shares,
    } for item in current_portfolio.items]


def get_portfolio_history(
    clerk_id: str,
    period: Optional[str] = None,
    timeframe: Optional[str] = None,
    extended_hours: Optional[bool] = None,
) -> Dict:
    """
    Get historical portfolio equity and P&L over time from broker.

    Args:
        clerk_id: Clerk authentication ID
        period: Time period (e.g. '1M', '3M', '1A', 'all')
        timeframe: Data resolution (e.g. '1D', '1H', '15Min')
        extended_hours: Include extended hours data

    Returns:
        Dict with timestamp, equity, profit_loss, etc.
    """
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_portfolio_history(
        account_id, period=period, timeframe=timeframe,
        extended_hours=extended_hours,
    )
