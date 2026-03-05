"""User portfolio repository — DB portfolio data and broker performance history."""

from typing import Optional, Dict
from app.db.core.models.user_data_models import *
from sqlalchemy.orm import selectinload
from app.utils.decorators.database import with_session
from app.repositories.user.broker import get_snaptrade_broker, resolve_snaptrade_credentials


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
    start_date: str,
    end_date: str,
) -> Dict:
    """
    Get historical portfolio performance report from SnapTrade.

    Args:
        clerk_id: Clerk authentication ID
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Dict with performance data (returns, equity curve, etc.)
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_performance_report(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        start_date=start_date,
        end_date=end_date,
        accounts=creds["snaptrade_account_id"],
    )
