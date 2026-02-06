"""Portfolio create, update, and delete operations."""

import logging
import uuid
from typing import List, Optional, Dict

from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.user_data_models import *
from app.db.core.models.market_data_models import *
from app.utils.time_utils import get_current_utc_time
from app.utils.decorators.database import with_session, with_transaction, with_sessions
from app.core.calculations.portfolio.utils import calc_num_shares, calc_position_navs


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

    Uses smart detection to only calculate what's missing:
    - If position has num_shares and position_nav: use them directly (no API calls)
    - If position has num_shares but no position_nav: calculate NAV from actual shares
    - If position has neither: calculate both from allocation + portfolio_value

    Args:
        portfolio: List of Position objects with ticker, allocation, and optionally
                  num_shares and position_nav
        user_id: User's UUID
        portfolio_name: Name for the portfolio
        portfolio_value: Optional total portfolio value (NAV). Required if positions
                        don't have num_shares.

    Flows:
        - Broker sync: Provides num_shares + position_nav → 0 API calls
        - Allocator: Provides num_shares only → 1 API call (for position_nav)
        - API create: Provides allocation only → 2 API calls (for both)
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

    # Step 1: Determine final num_shares for each position
    final_shares: Dict[str, int] = {}
    tickers_needing_shares = []

    for pos in portfolio:
        provided_shares = getattr(pos, 'num_shares', None)
        if provided_shares is not None:
            final_shares[pos.ticker] = provided_shares
        else:
            tickers_needing_shares.append(pos)

    # Calculate num_shares only for positions that need it
    if tickers_needing_shares:
        if portfolio_value is None:
            logging.warning(
                f"Positions {[p.ticker for p in tickers_needing_shares]} need num_shares "
                "but no portfolio_value provided"
            )
        else:
            weights = {p.ticker: p.allocation for p in tickers_needing_shares}
            try:
                calculated_shares = calc_num_shares(weights, portfolio_value)
                final_shares.update(calculated_shares)
            except ValueError as e:
                logging.warning(f"Could not calculate num_shares: {e}")

    # Step 2: Determine final position_nav for each position
    final_navs: Dict[str, float] = {}
    tickers_needing_nav = []

    for pos in portfolio:
        provided_nav = getattr(pos, 'position_nav', None)
        if provided_nav is not None:
            final_navs[pos.ticker] = provided_nav
        elif pos.ticker in final_shares:
            tickers_needing_nav.append(pos.ticker)

    # Calculate position_nav from ACTUAL final shares (not recalculated)
    if tickers_needing_nav:
        shares_for_calc = {t: final_shares[t] for t in tickers_needing_nav}
        try:
            calculated_navs = calc_position_navs(shares_for_calc)
            final_navs.update(calculated_navs)
        except Exception as e:
            logging.warning(f"Could not calculate position_navs: {e}")

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
        item = PortfolioItem(
            portfolio_id=portfolio_uuid,
            ticker=position.ticker,
            allocation=position.allocation,
            num_shares=final_shares.get(position.ticker),
            position_nav=final_navs.get(position.ticker),
            created_date=now,
            updated_date=now,
        )
        user_session.add(item)

    user_session.commit()
    return portfolio_uuid


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

    Uses smart detection to only calculate what's missing:
    - If position has num_shares and position_nav: use them directly (no API calls)
    - If position has num_shares but no position_nav: calculate NAV from actual shares
    - If position has neither: calculate both from allocation + nav

    Args:
        email: User email
        user_id: User UUID
        portfolio_id: Portfolio UUID to update
        name: Optional new name for the portfolio
        nav: Optional new NAV (portfolio value). If provided with positions,
             will calculate num_shares for positions that don't have them.
        is_current: Optional flag to set as current portfolio
        positions: Optional dict to replace all positions. Supports two formats:
                   - Simple: {ticker: allocation} - allocation only
                   - Extended: {ticker: {"allocation": float, "num_shares": int, "position_nav": float}}

    Returns:
        True if update succeeded, False if portfolio not found
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

        # Normalize positions to extract allocation, num_shares, and position_nav
        # Supports both {ticker: allocation} and {ticker: {allocation, num_shares, position_nav}}
        normalized_positions = {}
        for ticker, value in positions.items():
            if isinstance(value, dict):
                # Extended format: {allocation: float, num_shares: int, position_nav: float}
                normalized_positions[ticker] = {
                    'allocation': value.get('allocation'),
                    'num_shares': value.get('num_shares'),
                    'position_nav': value.get('position_nav'),
                }
            else:
                # Simple format: just allocation
                normalized_positions[ticker] = {
                    'allocation': value,
                    'num_shares': None,
                    'position_nav': None,
                }

        # Step 1: Calculate num_shares for positions that need them
        effective_nav = nav if nav is not None else portfolio.nav
        if effective_nav is not None:
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

        # Step 2: Calculate position_nav only for positions that need it
        # (have num_shares but no position_nav)
        tickers_needing_nav = [
            ticker for ticker, data in normalized_positions.items()
            if data['num_shares'] is not None and data['position_nav'] is None
        ]
        if tickers_needing_nav:
            shares_for_calc = {
                t: normalized_positions[t]['num_shares'] for t in tickers_needing_nav
            }
            try:
                calculated_navs = calc_position_navs(shares_for_calc)
                for ticker, nav_value in calculated_navs.items():
                    normalized_positions[ticker]['position_nav'] = nav_value
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
                position_nav=data['position_nav'],
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
