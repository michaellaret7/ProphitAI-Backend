"""Read-only portfolio query operations."""

import uuid
from typing import List, Optional, Dict

from sqlalchemy.orm import joinedload

from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.user_data_models import *
from app.db.core.models.market_data_models import *
from app.utils.decorators.database import with_session, with_sessions


def _flatten_portfolio_to_legacy_format(
    portfolios: List[Portfolio],
    market_session
) -> list[dict]:
    """
    Transform normalized Portfolio + PortfolioItem into legacy flat format.
    Uses batch fetching to avoid N+1 queries.

    Args:
        portfolios: List of Portfolio objects with items eagerly loaded
        market_session: Market database session for ticker lookups

    Returns:
        List of dicts in legacy flat format (one dict per position)
    """
    if not portfolios:
        return []

    # Collect all unique tickers across all portfolios
    all_tickers = set()
    for portfolio in portfolios:
        for item in portfolio.items:
            all_tickers.add(item.ticker)

    # Batch fetch ticker metadata
    ticker_map = {}
    if all_tickers:
        tickers = market_session.query(Ticker).filter(
            Ticker.ticker.in_(list(all_tickers))
        ).all()
        ticker_map = {t.ticker: t for t in tickers}

    # Flatten to legacy format
    result = []
    for portfolio in portfolios:
        for item in portfolio.items:
            ticker_data = ticker_map.get(item.ticker)
            result.append({
                'portfolio_id': str(portfolio.id),
                'name': portfolio.name,
                'nav': portfolio.nav,
                'ticker': item.ticker,
                'allocation': item.allocation,
                'num_shares': item.num_shares,
                'position_nav': item.position_nav,
                'sector': ticker_data.sector if ticker_data else None,
                'industry': ticker_data.industry if ticker_data else None,
                'sub_industry': ticker_data.sub_industry if ticker_data else None,
                'is_current': portfolio.is_current,
                'is_discretionary': portfolio.is_discretionary,
                'supporting_metrics': item.supporting_metrics,
                'reason_for_rec': item.reason_for_rec,
                'created_date': portfolio.created_date.isoformat() if portfolio.created_date else None,
                'updated_date': item.updated_date.isoformat() if item.updated_date else None,
                'user_id': str(portfolio.user_id),
            })
    return result


@with_sessions(user_session='user', market_session='market')
def retrieve_portfolio(email: str = None, clerk_id: str = None, user_id: uuid.UUID = None, is_current: bool = None, portfolio_id: uuid.UUID = None, user_session=None, market_session=None):
    """
    Retrieve portfolio(s) with all positions in legacy flat format.

    Args:
        email: User email
        clerk_id: Clerk user ID
        user_id: User UUID
        is_current: Filter for current portfolios only
        portfolio_id: Specific portfolio UUID to retrieve

    Returns:
        List of dicts in flat format (one dict per position with ticker metadata)
    """
    # If portfolio_id is provided, query directly by portfolio id (no user lookup needed)
    if portfolio_id:
        query = user_session.query(Portfolio).options(
            joinedload(Portfolio.items)
        ).filter(Portfolio.id == portfolio_id)
        portfolios = query.all()
        return _flatten_portfolio_to_legacy_format(portfolios, market_session)

    # Otherwise, require a user identifier
    user = None
    if user_id:
        user = user_session.query(User).filter(User.id == user_id).first()
    elif email:
        user = user_session.query(User).filter(User.email == email).first()
    elif clerk_id:
        user = user_session.query(User).filter(User.clerk_id == clerk_id).first()
    else:
        raise ValueError("At least one identifier (email, clerk_id, user_id, or portfolio_id) must be provided")

    if not user:
        return []

    # Build the query based on parameters
    query = user_session.query(Portfolio).options(
        joinedload(Portfolio.items)
    ).filter(Portfolio.user_id == user.id)

    if is_current:
        query = query.filter(Portfolio.is_current == True)

    portfolios = query.all()
    return _flatten_portfolio_to_legacy_format(portfolios, market_session)


@with_sessions(user_session='user', market_session='market')
def retrieve_portfolios_batch(
    portfolio_ids: List[uuid.UUID],
    user_session=None,
    market_session=None
) -> Dict[str, List[Dict]]:
    """
    Retrieve multiple portfolios with positions in a single optimized query.

    Args:
        portfolio_ids: List of portfolio UUIDs to retrieve

    Returns:
        Dict mapping portfolio_id (str) -> list of position dicts
    """
    if not portfolio_ids:
        return {}

    # Single query with eager loading for all portfolios
    portfolios = user_session.query(Portfolio).options(
        joinedload(Portfolio.items)
    ).filter(Portfolio.id.in_(portfolio_ids)).all()

    if not portfolios:
        return {}

    # Batch fetch all unique tickers across all portfolios
    all_tickers = set()
    for portfolio in portfolios:
        for item in portfolio.items:
            all_tickers.add(item.ticker)

    ticker_map = {}
    if all_tickers:
        tickers = market_session.query(Ticker).filter(
            Ticker.ticker.in_(list(all_tickers))
        ).all()
        ticker_map = {t.ticker: t for t in tickers}

    # Build result dict: portfolio_id -> positions list
    result = {}
    for portfolio in portfolios:
        portfolio_id = str(portfolio.id)
        positions = []
        for item in portfolio.items:
            ticker_data = ticker_map.get(item.ticker)
            positions.append({
                'portfolio_id': portfolio_id,
                'name': portfolio.name,
                'nav': portfolio.nav,
                'ticker': item.ticker,
                'allocation': item.allocation,
                'num_shares': item.num_shares,
                'position_nav': item.position_nav,
                'sector': ticker_data.sector if ticker_data else None,
                'industry': ticker_data.industry if ticker_data else None,
                'sub_industry': ticker_data.sub_industry if ticker_data else None,
                'is_current': portfolio.is_current,
                'is_discretionary': portfolio.is_discretionary,
                'supporting_metrics': item.supporting_metrics,
                'reason_for_rec': item.reason_for_rec,
                'created_date': portfolio.created_date.isoformat() if portfolio.created_date else None,
                'updated_date': item.updated_date.isoformat() if item.updated_date else None,
                'user_id': str(portfolio.user_id),
            })
        result[portfolio_id] = positions

    return result


@with_session('user')
def list_portfolios(email: str = None, clerk_id: str = None, user_id: uuid.UUID = None, session=None):
    """
    List all portfolios for a user (metadata only, no positions).

    Returns:
        List of dicts with portfolio_id, name, is_current, is_discretionary, created_date, user_id
    """
    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    elif clerk_id:
        user = session.query(User).filter(User.clerk_id == clerk_id).first()
    else:
        raise ValueError("At least one identifier (email, clerk_id, or user_id) must be provided")

    if not user:
        return []

    # Simple query - one row per portfolio in new schema
    portfolios = session.query(Portfolio).filter(Portfolio.user_id == user.id).all()

    return [{
        'portfolio_id': str(p.id),
        'name': p.name,
        'nav': p.nav,
        'is_current': p.is_current,
        'is_discretionary': p.is_discretionary,
        'created_date': p.created_date.isoformat() if p.created_date else None,
        'user_id': str(p.user_id)
    } for p in portfolios]


@with_session('user')
def get_all_portfolio_ids(email: str = None, user_id: uuid.UUID = None, session=None):
    """
    Get all portfolio IDs for a user.

    Args:
        email: User email
        user_id: User UUID
        session: Database session (injected by decorator)

    Returns:
        List of portfolio UUIDs
    """
    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    else:
        raise ValueError("At least one identifier (email or user_id) must be provided")

    if not user:
        return []

    # Get portfolio IDs for the user (one row per portfolio in new schema)
    portfolio_ids = session.query(Portfolio.id).filter(
        Portfolio.user_id == user.id
    ).all()

    return [pid[0] for pid in portfolio_ids]
