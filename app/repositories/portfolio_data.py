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


# =============================================================================
# PORTFOLIO PREFERENCES
# =============================================================================

@with_session('user')
def get_portfolio_preference(portfolio_id: uuid.UUID, session=None) -> Optional[Dict]:
    """
    Get portfolio preferences by portfolio ID.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        Dictionary containing preference data, or None if not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    preference = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()

    if not preference:
        return None

    return {
        'id': preference.id,
        'portfolio_id': str(preference.portfolio_id),
        'description': preference.description,
        # Risk Profile
        'risk_tolerance': preference.risk_tolerance,
        'investment_time_horizon': preference.investment_time_horizon,
        'liquidity_needs': preference.liquidity_needs,
        # Asset Allocations
        'equities_allocation': float(preference.equities_allocation) if preference.equities_allocation else None,
        'fixed_income_allocation': float(preference.fixed_income_allocation) if preference.fixed_income_allocation else None,
        'commodities_allocation': float(preference.commodities_allocation) if preference.commodities_allocation else None,
        'currencies_allocation': float(preference.currencies_allocation) if preference.currencies_allocation else None,
        'cryptocurrencies_allocation': float(preference.cryptocurrencies_allocation) if preference.cryptocurrencies_allocation else None,
        'alternatives_hedge_funds_allocation': float(preference.alternatives_hedge_funds_allocation) if preference.alternatives_hedge_funds_allocation else None,
        'alternatives_pe_vc_allocation': float(preference.alternatives_pe_vc_allocation) if preference.alternatives_pe_vc_allocation else None,
        'cash_allocation': float(preference.cash_allocation) if preference.cash_allocation else None,
        # Equity Sector Preferences
        'equity_sector_communication_services': preference.equity_sector_communication_services,
        'equity_sector_consumer_discretionary': preference.equity_sector_consumer_discretionary,
        'equity_sector_consumer_staples': preference.equity_sector_consumer_staples,
        'equity_sector_energy': preference.equity_sector_energy,
        'equity_sector_financials': preference.equity_sector_financials,
        'equity_sector_health_care': preference.equity_sector_health_care,
        'equity_sector_industrials': preference.equity_sector_industrials,
        'equity_sector_information_technology': preference.equity_sector_information_technology,
        'equity_sector_materials': preference.equity_sector_materials,
        'equity_sector_real_estate': preference.equity_sector_real_estate,
        'equity_sector_utilities': preference.equity_sector_utilities,
        # Fixed Income Sector Preferences
        'fixed_income_sector_sovereign_treasuries': preference.fixed_income_sector_sovereign_treasuries,
        'fixed_income_sector_ig_credit': preference.fixed_income_sector_ig_credit,
        'fixed_income_sector_high_yield': preference.fixed_income_sector_high_yield,
        'fixed_income_sector_securitized_products': preference.fixed_income_sector_securitized_products,
        # Ticker Lists
        'tickers_to_include': preference.tickers_to_include,
        'tickers_to_exclude': preference.tickers_to_exclude,
        # Timestamps
        'created_date': preference.created_date.isoformat() if preference.created_date else None,
        'updated_date': preference.updated_date.isoformat() if preference.updated_date else None,
    }


@with_transaction('user')
def create_portfolio_preference(
    portfolio_id: uuid.UUID,
    description: Optional[str] = None,
    risk_tolerance: Optional[str] = None,
    investment_time_horizon: Optional[str] = None,
    liquidity_needs: Optional[str] = None,
    equities_allocation: Optional[float] = None,
    fixed_income_allocation: Optional[float] = None,
    commodities_allocation: Optional[float] = None,
    currencies_allocation: Optional[float] = None,
    cryptocurrencies_allocation: Optional[float] = None,
    alternatives_hedge_funds_allocation: Optional[float] = None,
    alternatives_pe_vc_allocation: Optional[float] = None,
    cash_allocation: Optional[float] = None,
    equity_sector_communication_services: Optional[str] = None,
    equity_sector_consumer_discretionary: Optional[str] = None,
    equity_sector_consumer_staples: Optional[str] = None,
    equity_sector_energy: Optional[str] = None,
    equity_sector_financials: Optional[str] = None,
    equity_sector_health_care: Optional[str] = None,
    equity_sector_industrials: Optional[str] = None,
    equity_sector_information_technology: Optional[str] = None,
    equity_sector_materials: Optional[str] = None,
    equity_sector_real_estate: Optional[str] = None,
    equity_sector_utilities: Optional[str] = None,
    fixed_income_sector_sovereign_treasuries: Optional[str] = None,
    fixed_income_sector_ig_credit: Optional[str] = None,
    fixed_income_sector_high_yield: Optional[str] = None,
    fixed_income_sector_securitized_products: Optional[str] = None,
    tickers_to_include: Optional[List[str]] = None,
    tickers_to_exclude: Optional[List[str]] = None,
    session=None
) -> Dict:
    """
    Create portfolio preferences for a portfolio.

    Args:
        portfolio_id: Portfolio UUID (must exist)
        description: Portfolio description
        risk_tolerance: One of 'Capital Preservation', 'Income', 'Balanced/Moderate Growth',
                       'Growth', 'Aggressive Growth/Speculation'
        investment_time_horizon: One of 'Short term (0-2 years)', 'Medium term (3-7 years)',
                                'Long term (8+ years)'
        liquidity_needs: One of 'High', 'Medium', 'Low'
        *_allocation: Decimal values 0-1 for asset class allocations
        equity_sector_*: One of 'Include', 'Exclude', 'Not Selected'
        fixed_income_sector_*: One of 'Include', 'Exclude', 'Not Selected'
        tickers_to_include: List of tickers to include
        tickers_to_exclude: List of tickers to exclude

    Returns:
        Dictionary containing the created preference data

    Raises:
        ValueError: If portfolio doesn't exist or preference already exists
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    # Verify portfolio exists
    portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    # Check if preference already exists
    existing = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()
    if existing:
        raise ValueError(f"Preference already exists for portfolio {portfolio_id}")

    now = get_current_utc_time()
    preference = PortfolioPreference(
        portfolio_id=portfolio_id,
        description=description,
        risk_tolerance=risk_tolerance,
        investment_time_horizon=investment_time_horizon,
        liquidity_needs=liquidity_needs,
        equities_allocation=equities_allocation,
        fixed_income_allocation=fixed_income_allocation,
        commodities_allocation=commodities_allocation,
        currencies_allocation=currencies_allocation,
        cryptocurrencies_allocation=cryptocurrencies_allocation,
        alternatives_hedge_funds_allocation=alternatives_hedge_funds_allocation,
        alternatives_pe_vc_allocation=alternatives_pe_vc_allocation,
        cash_allocation=cash_allocation,
        equity_sector_communication_services=equity_sector_communication_services or 'Not Selected',
        equity_sector_consumer_discretionary=equity_sector_consumer_discretionary or 'Not Selected',
        equity_sector_consumer_staples=equity_sector_consumer_staples or 'Not Selected',
        equity_sector_energy=equity_sector_energy or 'Not Selected',
        equity_sector_financials=equity_sector_financials or 'Not Selected',
        equity_sector_health_care=equity_sector_health_care or 'Not Selected',
        equity_sector_industrials=equity_sector_industrials or 'Not Selected',
        equity_sector_information_technology=equity_sector_information_technology or 'Not Selected',
        equity_sector_materials=equity_sector_materials or 'Not Selected',
        equity_sector_real_estate=equity_sector_real_estate or 'Not Selected',
        equity_sector_utilities=equity_sector_utilities or 'Not Selected',
        fixed_income_sector_sovereign_treasuries=fixed_income_sector_sovereign_treasuries or 'Not Selected',
        fixed_income_sector_ig_credit=fixed_income_sector_ig_credit or 'Not Selected',
        fixed_income_sector_high_yield=fixed_income_sector_high_yield or 'Not Selected',
        fixed_income_sector_securitized_products=fixed_income_sector_securitized_products or 'Not Selected',
        tickers_to_include=tickers_to_include,
        tickers_to_exclude=tickers_to_exclude,
        created_date=now,
        updated_date=now,
    )
    session.add(preference)
    session.flush()

    return {
        'id': preference.id,
        'portfolio_id': str(preference.portfolio_id),
        'created_date': preference.created_date.isoformat(),
    }


@with_transaction('user')
def update_portfolio_preference(
    portfolio_id: uuid.UUID,
    description: Optional[str] = None,
    risk_tolerance: Optional[str] = None,
    investment_time_horizon: Optional[str] = None,
    liquidity_needs: Optional[str] = None,
    equities_allocation: Optional[float] = None,
    fixed_income_allocation: Optional[float] = None,
    commodities_allocation: Optional[float] = None,
    currencies_allocation: Optional[float] = None,
    cryptocurrencies_allocation: Optional[float] = None,
    alternatives_hedge_funds_allocation: Optional[float] = None,
    alternatives_pe_vc_allocation: Optional[float] = None,
    cash_allocation: Optional[float] = None,
    equity_sector_communication_services: Optional[str] = None,
    equity_sector_consumer_discretionary: Optional[str] = None,
    equity_sector_consumer_staples: Optional[str] = None,
    equity_sector_energy: Optional[str] = None,
    equity_sector_financials: Optional[str] = None,
    equity_sector_health_care: Optional[str] = None,
    equity_sector_industrials: Optional[str] = None,
    equity_sector_information_technology: Optional[str] = None,
    equity_sector_materials: Optional[str] = None,
    equity_sector_real_estate: Optional[str] = None,
    equity_sector_utilities: Optional[str] = None,
    fixed_income_sector_sovereign_treasuries: Optional[str] = None,
    fixed_income_sector_ig_credit: Optional[str] = None,
    fixed_income_sector_high_yield: Optional[str] = None,
    fixed_income_sector_securitized_products: Optional[str] = None,
    tickers_to_include: Optional[List[str]] = None,
    tickers_to_exclude: Optional[List[str]] = None,
    session=None
) -> bool:
    """
    Update portfolio preferences. Only provided fields are updated.

    Args:
        portfolio_id: Portfolio UUID
        [other args]: Fields to update (None values are ignored)

    Returns:
        True if updated, False if preference not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    preference = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).first()

    if not preference:
        return False

    # Update only provided fields
    if description is not None:
        preference.description = description
    if risk_tolerance is not None:
        preference.risk_tolerance = risk_tolerance
    if investment_time_horizon is not None:
        preference.investment_time_horizon = investment_time_horizon
    if liquidity_needs is not None:
        preference.liquidity_needs = liquidity_needs
    if equities_allocation is not None:
        preference.equities_allocation = equities_allocation
    if fixed_income_allocation is not None:
        preference.fixed_income_allocation = fixed_income_allocation
    if commodities_allocation is not None:
        preference.commodities_allocation = commodities_allocation
    if currencies_allocation is not None:
        preference.currencies_allocation = currencies_allocation
    if cryptocurrencies_allocation is not None:
        preference.cryptocurrencies_allocation = cryptocurrencies_allocation
    if alternatives_hedge_funds_allocation is not None:
        preference.alternatives_hedge_funds_allocation = alternatives_hedge_funds_allocation
    if alternatives_pe_vc_allocation is not None:
        preference.alternatives_pe_vc_allocation = alternatives_pe_vc_allocation
    if cash_allocation is not None:
        preference.cash_allocation = cash_allocation
    if equity_sector_communication_services is not None:
        preference.equity_sector_communication_services = equity_sector_communication_services
    if equity_sector_consumer_discretionary is not None:
        preference.equity_sector_consumer_discretionary = equity_sector_consumer_discretionary
    if equity_sector_consumer_staples is not None:
        preference.equity_sector_consumer_staples = equity_sector_consumer_staples
    if equity_sector_energy is not None:
        preference.equity_sector_energy = equity_sector_energy
    if equity_sector_financials is not None:
        preference.equity_sector_financials = equity_sector_financials
    if equity_sector_health_care is not None:
        preference.equity_sector_health_care = equity_sector_health_care
    if equity_sector_industrials is not None:
        preference.equity_sector_industrials = equity_sector_industrials
    if equity_sector_information_technology is not None:
        preference.equity_sector_information_technology = equity_sector_information_technology
    if equity_sector_materials is not None:
        preference.equity_sector_materials = equity_sector_materials
    if equity_sector_real_estate is not None:
        preference.equity_sector_real_estate = equity_sector_real_estate
    if equity_sector_utilities is not None:
        preference.equity_sector_utilities = equity_sector_utilities
    if fixed_income_sector_sovereign_treasuries is not None:
        preference.fixed_income_sector_sovereign_treasuries = fixed_income_sector_sovereign_treasuries
    if fixed_income_sector_ig_credit is not None:
        preference.fixed_income_sector_ig_credit = fixed_income_sector_ig_credit
    if fixed_income_sector_high_yield is not None:
        preference.fixed_income_sector_high_yield = fixed_income_sector_high_yield
    if fixed_income_sector_securitized_products is not None:
        preference.fixed_income_sector_securitized_products = fixed_income_sector_securitized_products
    if tickers_to_include is not None:
        preference.tickers_to_include = tickers_to_include
    if tickers_to_exclude is not None:
        preference.tickers_to_exclude = tickers_to_exclude

    preference.updated_date = get_current_utc_time()
    return True


@with_transaction('user')
def delete_portfolio_preference(portfolio_id: uuid.UUID, session=None) -> bool:
    """
    Delete portfolio preferences for a portfolio.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        True if deleted, False if not found
    """
    if not portfolio_id:
        raise ValueError("portfolio_id must be provided")

    result = session.query(PortfolioPreference).filter(
        PortfolioPreference.portfolio_id == portfolio_id
    ).delete(synchronize_session=False)

    return result > 0

