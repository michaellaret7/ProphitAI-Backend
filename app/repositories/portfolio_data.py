import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from sqlalchemy import func
from sqlalchemy.orm import aliased, joinedload

from app.db.core.db_config import UserSession, MarketSession, ProphitAltsSession
from app.db.core.models.user_data_models import *
from app.db.core.models.market_data_models import *
from app.db.core.models.prophit_alts_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.time_utils import get_current_utc_time
from app.utils.decorators.database import with_session, with_transaction, with_sessions
from app.core.calculations.portfolio.utils import calc_num_shares, calc_position_navs


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
def add_portfolio(
    portfolio,
    user_id: uuid.UUID,
    portfolio_name: str,
    portfolio_value: Optional[float] = None,
    user_session=None,
    market_session=None
):
    """
    Add a new portfolio for a user.

    Args:
        portfolio: List of Position objects with ticker, allocation, and optionally num_shares
        user_id: User's UUID
        portfolio_name: Name for the portfolio
        portfolio_value: Optional total portfolio value (NAV). If provided and positions
                        don't have num_shares, will calculate num_shares from allocations.

    Note:
        If portfolio_value is provided, num_shares will be calculated for each position
        using: num_shares = allocation * portfolio_value / current_price

        If positions already have num_shares set, those values will be used instead.
    """
    user = user_session.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    # Validate all tickers exist before creating anything
    for position in portfolio:
        ticker_data = market_session.query(Ticker).filter(Ticker.ticker == position.ticker).first()
        if not ticker_data:
            raise ValueError(f"Ticker {position.ticker} not found")

    portfolio_uuid = uuid.uuid4()
    now = get_current_utc_time()

    # Calculate num_shares if portfolio_value is provided
    num_shares_map: Dict[str, float] = {}
    position_nav_map: Dict[str, float] = {}
    if portfolio_value is not None:
        # Build weights dict from positions
        weights = {pos.ticker: pos.allocation for pos in portfolio}
        try:
            num_shares_map = calc_num_shares(weights, portfolio_value)
            # Calculate position NAVs from the num_shares we just calculated
            position_nav_map = calc_position_navs(num_shares_map)
        except ValueError as e:
            # If price fetch fails, log warning but continue without num_shares
            logging.warning(f"Could not calculate num_shares: {e}")

    # Create one Portfolio record
    new_portfolio = Portfolio(
        id=portfolio_uuid,
        user_id=user.id,
        name=portfolio_name,
        nav=portfolio_value,
        is_current=False,
        is_discretionary=False,
        created_date=now,
        updated_date=now,
    )
    user_session.add(new_portfolio)

    # Create PortfolioItem records for each position
    for position in portfolio:
        # Use num_shares from position if available, otherwise from calculated map
        position_num_shares = getattr(position, 'num_shares', None)
        if position_num_shares is None:
            position_num_shares = num_shares_map.get(position.ticker)

        # Get position_nav from calculated map
        position_nav = position_nav_map.get(position.ticker)

        item = PortfolioItem(
            portfolio_id=portfolio_uuid,
            ticker=position.ticker,
            allocation=position.allocation,
            num_shares=position_num_shares,
            position_nav=position_nav,
            created_date=now,
            updated_date=now,
        )
        user_session.add(item)

    user_session.commit()
    return portfolio_uuid

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

@with_sessions(prophit_session='prophit', market_session='market')
def add_initial_positions(positions: dict, industry: str, fund_name: str, prophit_session=None, market_session=None):
    for position in positions['long']:
        prophit_session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=prophit_session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.LONG,
            industry=industry,
            conviction=position['allocation'],  # Already decimal format (0.25 = 25%)
            reasoning=position['reasoning'],
            date_created=get_current_utc_time(),
            date_updated=get_current_utc_time(),
        ))

    for position in positions['short']:
        prophit_session.add(FundInitialPosition(
            id=uuid.uuid4(),
            fund_id=prophit_session.query(Fund).filter(Fund.fund_name == fund_name).first().id,
            fund_name=fund_name,
            ticker_id=market_session.query(Ticker).filter(Ticker.ticker == position['ticker']).first().id,
            ticker_name=position['ticker'],
            position=PositionType.SHORT,
            industry=industry,
            conviction=position['allocation'],  # Already decimal format (0.25 = 25%)
            reasoning=position['reasoning'],
            date_created=get_current_utc_time(),
            date_updated=get_current_utc_time(),
        ))   

    # Commit the transaction for prophit_session
    prophit_session.commit()
    
    return True

@with_sessions(user_session='user', market_session='market')
def update_portfolio(
    *,
    email: str = None,
    user_id: uuid.UUID = None,
    portfolio_id: uuid.UUID = None,
    name: Optional[str] = None,
    nav: Optional[float] = None,
    is_current: Optional[bool] = None,
    positions: Optional[dict] = None,
    user_session=None,
    market_session=None
) -> bool:
    """
    Update an existing portfolio's metadata and/or positions.

    Args:
        email: User email
        user_id: User UUID
        portfolio_id: Portfolio UUID to update
        name: Optional new name for the portfolio
        nav: Optional new NAV (portfolio value). If provided with positions,
             will recalculate num_shares for each position.
        is_current: Optional flag to set as current portfolio
        positions: Optional dict to replace all positions. Supports two formats:
                   - Simple: {ticker: allocation} - allocation only
                   - Extended: {ticker: {"allocation": float, "num_shares": float}} - both fields

    Returns:
        True if update succeeded, False if portfolio not found

    Note:
        When positions are updated:
        - If nav is provided and positions use simple format, num_shares will be calculated
        - If positions use extended format with num_shares, those values are used directly
        - If neither nav nor num_shares provided, num_shares will be None
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    user = None
    if user_id:
        user = user_session.query(User).filter(User.id == user_id).first()
    elif email:
        user = user_session.query(User).filter(User.email == email).first()
    else:
        raise ValueError("At least one identifier (email or user_id) must be provided")

    if not user:
        return False

    # Find the portfolio
    portfolio = user_session.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.id == portfolio_id
    ).first()

    if not portfolio:
        return False

    # Update metadata if provided
    if name is not None:
        portfolio.name = name
    if nav is not None:
        portfolio.nav = nav
    if is_current is not None:
        portfolio.is_current = is_current
    portfolio.updated_date = get_current_utc_time()

    # Update positions if provided
    if positions is not None:
        # Validate all tickers exist before making changes
        for ticker in positions.keys():
            ticker_data = market_session.query(Ticker).filter(Ticker.ticker == ticker).first()
            if not ticker_data:
                raise ValueError(f"Ticker {ticker} not found")

        # Normalize positions to extract allocation and num_shares
        # Supports both {ticker: allocation} and {ticker: {allocation, num_shares}}
        normalized_positions = {}
        for ticker, value in positions.items():
            if isinstance(value, dict):
                # Extended format: {allocation: float, num_shares: float}
                normalized_positions[ticker] = {
                    'allocation': value.get('allocation'),
                    'num_shares': value.get('num_shares'),
                }
            else:
                # Simple format: just allocation
                normalized_positions[ticker] = {
                    'allocation': value,
                    'num_shares': None,
                }

        # Calculate num_shares if nav is available and positions don't have them
        effective_nav = nav if nav is not None else portfolio.nav
        if effective_nav is not None:
            # Build weights for positions missing num_shares
            weights_needing_shares = {
                ticker: data['allocation']
                for ticker, data in normalized_positions.items()
                if data['num_shares'] is None and data['allocation'] is not None
            }
            if weights_needing_shares:
                try:
                    calculated_shares = calc_num_shares(weights_needing_shares, effective_nav)
                    for ticker, shares in calculated_shares.items():
                        normalized_positions[ticker]['num_shares'] = shares
                except ValueError as e:
                    logging.warning(f"Could not calculate num_shares during update: {e}")

        # Calculate position_navs for all positions that have num_shares
        positions_for_nav = {
            ticker: data['num_shares']
            for ticker, data in normalized_positions.items()
            if data['num_shares'] is not None
        }
        position_nav_map = {}
        if positions_for_nav:
            try:
                position_nav_map = calc_position_navs(positions_for_nav)
            except Exception as e:
                logging.warning(f"Could not calculate position_navs during update: {e}")

        # Delete all existing PortfolioItems
        user_session.query(PortfolioItem).filter(
            PortfolioItem.portfolio_id == portfolio_id
        ).delete(synchronize_session=False)

        # Add new PortfolioItems
        now = get_current_utc_time()
        for ticker, data in normalized_positions.items():
            item = PortfolioItem(
                portfolio_id=portfolio_id,
                ticker=ticker,
                allocation=data['allocation'],
                num_shares=data['num_shares'],
                position_nav=position_nav_map.get(ticker),
                created_date=now,
                updated_date=now,
            )
            user_session.add(item)

    user_session.commit()
    return True

@with_transaction('user')
def delete_portfolio(
    *,
    email: str = None,
    user_id: uuid.UUID = None,
    portfolio_id: uuid.UUID = None,
    session=None
) -> bool:
    """
    Delete a portfolio by ID. CASCADE will auto-delete PortfolioItems.

    Returns:
        True if deleted, False if not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    else:
        raise ValueError("At least one identifier (email or user_id) must be provided")

    if not user:
        return False

    q = session.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.id == portfolio_id
    )
    count = q.count()
    if count == 0:
        return False

    q.delete(synchronize_session=False)
    # commit handled by decorator
    return True

@with_transaction('user')
def delete_portfolio_by_name(
    *,
    portfolio_name: str,
    email: str = None,
    user_id: uuid.UUID = None,
    session=None
) -> int:
    """
    Delete all portfolios with the given name. CASCADE will auto-delete PortfolioItems.

    Args:
        portfolio_name: Name of the portfolio(s) to delete
        email: User email
        user_id: User UUID
        session: Database session (injected by decorator)

    Returns:
        Number of portfolios deleted
    """
    if not portfolio_name:
        raise ValueError("portfolio_name must be provided")

    user = None
    if user_id:
        user = session.query(User).filter(User.id == user_id).first()
    elif email:
        user = session.query(User).filter(User.email == email).first()
    else:
        raise ValueError("At least one identifier (email or user_id) must be provided")

    if not user:
        return 0

    # Delete all portfolios with this name and user_id
    q = session.query(Portfolio).filter(
        Portfolio.user_id == user.id,
        Portfolio.name == portfolio_name
    )
    count = q.count()

    if count > 0:
        q.delete(synchronize_session=False)

    # commit handled by decorator
    return count

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

