from app.db.core.models.user_data_models import *
from app.db.core.db_config import UserSession
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional, Union, Dict, Any
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.decorators.database import with_session, with_transaction
from datetime import datetime
from app.utils.time_utils import get_current_utc_time
import uuid
from app.db.core.pull_fmp_data import FMP_API_DATA

@with_session('user')
def get_all_user_data(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by email
    
    Args:
        email: User's email address
        
    Returns:
        Dictionary containing complete user data with companies and portfolios, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")
    
    query = session.query(User).options(
        joinedload(User.company),
        selectinload(User.portfolios)
    )

    query = query.filter(User.email == email)

    user = query.first()

    if not user:
        return None

    # Format user data
    user_data = {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'creation_date': user.creation_date.isoformat() if getattr(user, 'creation_date', None) else None,
        'companies': [],
        'portfolios': []
    }

    # Add company information (single company per user)
    if user.company:
        company = user.company
        user_data['companies'].append({
            'id': str(company.id),
            'name': company.name,
            'creation_date': company.creation_date.isoformat() if company.creation_date else None,
            'seats': company.seats,
            'user_role': user.role
        })

    # Add portfolio information (one row per portfolio in new schema)
    for portfolio in user.portfolios:
        user_data['portfolios'].append({
            'name': portfolio.name,
            'portfolio_id': str(portfolio.id),
            'is_current': portfolio.is_current,
            'is_discretionary': portfolio.is_discretionary
        })

    return user_data

@with_session('user')
def get_all_user_data_by_id(user_id: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by internal user ID (UUID).

    Args:
        user_id: Internal database user UUID

    Returns:
        Dictionary containing complete user data, or None if not found
    """
    if not user_id:
        raise ValueError("User ID must be provided")

    query = session.query(User).options(
        joinedload(User.company),
        selectinload(User.portfolios)
    )
    query = query.filter(User.id == user_id)
    user = query.first()
    if not user:
        return None

    user_data = {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'creation_date': user.creation_date.isoformat() if getattr(user, 'creation_date', None) else None,
        'companies': [],
        'portfolios': []
    }
    if user.company:
        company = user.company
        user_data['companies'].append({
            'id': str(company.id),
            'name': company.name,
            'creation_date': company.creation_date.isoformat() if company.creation_date else None,
            'seats': company.seats,
            'user_role': user.role
        })
    for portfolio in user.portfolios:
        user_data['portfolios'].append({
            'name': portfolio.name,
            'portfolio_id': str(portfolio.id),
            'is_current': portfolio.is_current,
            'is_discretionary': portfolio.is_discretionary
        })
    return user_data


@with_session('user')
def get_all_user_data_by_clerk_id(clerk_id: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by Clerk ID
    """
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")

    query = session.query(User).options(
        joinedload(User.company),
        selectinload(User.portfolios)
    )
    query = query.filter(User.clerk_id == clerk_id)
    user = query.first()
    if not user:
        return None

    user_data = {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'creation_date': user.creation_date.isoformat() if getattr(user, 'creation_date', None) else None,
        'companies': [],
        'portfolios': []
    }
    if user.company:
        company = user.company
        user_data['companies'].append({
            'id': str(company.id),
            'name': company.name,
            'creation_date': company.creation_date.isoformat() if company.creation_date else None,
            'seats': company.seats,
            'user_role': user.role
        })
    for portfolio in user.portfolios:
        user_data['portfolios'].append({
            'name': portfolio.name,
            'portfolio_id': str(portfolio.id),
            'is_current': portfolio.is_current,
            'is_discretionary': portfolio.is_discretionary
        })
    return user_data

@with_session('user')
def get_user_basic_info(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get basic user info (id, email, first_name, last_name) by email
    
    Args:
        email: User's email address
        
    Returns:
        Dictionary containing only basic user info, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")
    
    query = session.query(User).filter(User.email == email)
    user = query.first()
    
    if not user:
        return None
    
    return {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name
    }

@with_session('user')
def email_exists(email: str, session=None) -> bool:
    """Check if a user with the given email exists."""
    if not email:
        return False
    return session.query(User).filter(User.email == email).first() is not None

@with_transaction('user')
def add_user(email: str, first_name: str, last_name: str, clerk_id: Optional[str] = None, session=None):
    user = session.query(User).filter(User.email == email).first()
    if user:
        # Return the existing user object for caller handling
        return user
    
    user = User(
        id = uuid.uuid4(),
        clerk_id=clerk_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        creation_date=get_current_utc_time()
    )

    session.add(user)
    return user

@with_transaction('user')
def update_user_clerk_id(email: str, clerk_id: str, session=None) -> None:
    user = session.query(User).filter(User.email == email).first()
    if user and user.clerk_id != clerk_id:
        user.clerk_id = clerk_id

@with_transaction('user')
def update_user_fields(
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    clerk_id: Optional[str] = None,
    company_name: Optional[str] = None,
    role: Optional[str] = None,
    session=None
) -> bool:
    if not email:
        raise ValueError("Email must be provided")

    user = session.query(User).filter(User.email == email).first()
    if not user:
        return False

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if clerk_id is not None:
        user.clerk_id = clerk_id
    if company_name is not None:
        company = session.query(Company).filter(Company.name == company_name).first()
        if not company:
            company = Company(id=uuid.uuid4(), name=company_name, creation_date=get_current_utc_time(), seats=0)
            session.add(company)
            session.flush()
        user.company_id = company.id
    if role is not None:
        user.role = role

    # commit handled by decorator
    return True

@with_transaction('user')
def update_user_by_clerk_id(
    clerk_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    session=None
) -> bool:
    """Update user fields by clerk_id."""
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")

    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        return False

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name

    return True

@with_transaction('user')
def assign_all_users_to_company_by_name(company_name: str, session=None) -> int:
    """
    Set company_id for all users to the ID of the company with the given name.
    Returns the number of rows updated.
    """
    company = session.query(Company).filter(Company.name == company_name).first()
    if not company:
        raise ValueError("Company not found")
    updated = session.query(User).update({User.company_id: company.id}, synchronize_session=False)
    return updated

@with_transaction('user')
def assign_all_users_to_prophitai(session=None) -> int:
    return assign_all_users_to_company_by_name('ProphitAI', session=session)

@with_transaction('user')
def set_all_users_to_admin(session=None) -> int:
    """
    Set role='admin' for all users. Returns number of rows updated.
    """
    updated = session.query(User).update({User.role: 'admin'}, synchronize_session=False)
    return updated

@with_transaction('user')
def assign_user_to_company_by_id(email: str, company_id: str, role: Optional[str] = None, session=None) -> bool:
    """Assign a user to a company by company ID."""
    user = session.query(User).filter(User.email == email).first()
    if not user:
        return False
    company = session.query(Company).filter(Company.id == company_id).first()
    if not company:
        return False
    user.company_id = company.id
    if role is not None:
        user.role = role
    return True

@with_transaction('user')
def add_company(company_name:str, seats:int, session=None):
    company = Company(
        id = uuid.uuid4(),
        name=company_name,
        creation_date=get_current_utc_time(),
        seats=seats
    )
    session.add(company)
    # commit handled by decorator

@with_session('user')
def get_user_current_portfolio(email: str, session=None):
    if not email:
        raise ValueError("Email must be provided")
    
    user = session.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    user_id = user.id

    portfolio = session.query(PortfolioItem).filter(PortfolioItem.user_id == user_id, PortfolioItem.is_current == True).all()
    portfolio = [serialize_sqlalchemy_obj(p) for p in portfolio]
    
    return portfolio

@with_transaction('user')
def delete_user_by_clerk_id(clerk_id: str, session=None) -> bool:
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        return False
    session.delete(user)
    return True

@with_session('user')
def get_user_watchlists(user_id: str, session=None):
    """Get all watchlists for a user with their items."""
    if not user_id:
        raise ValueError("User ID must be provided")

    watchlists = session.query(Watchlist).options(
        selectinload(Watchlist.items)
    ).filter(Watchlist.user_id == user_id).all()

    return [
        {
            'id': str(w.id),
            'name': w.name,
            'creation_date': w.creation_date.isoformat() if w.creation_date else None,
            'updated_date': w.updated_date.isoformat() if w.updated_date else None,
            'items': [
                {
                    'ticker': item.ticker,
                    'price_on_inception': item.price_on_inception,
                    'added_at': item.added_at.isoformat() if item.added_at else None
                }
                for item in w.items
            ]
        }
        for w in watchlists
    ]

@with_session('user')
def get_watchlist_by_id(watchlist_id: str, session=None):
    """Get a single watchlist by ID with its items."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")

    watchlist = session.query(Watchlist).options(
        selectinload(Watchlist.items)
    ).filter(Watchlist.id == watchlist_id).first()

    if not watchlist:
        return None

    return {
        'id': str(watchlist.id),
        'user_id': str(watchlist.user_id),
        'name': watchlist.name,
        'creation_date': watchlist.creation_date.isoformat() if watchlist.creation_date else None,
        'updated_date': watchlist.updated_date.isoformat() if watchlist.updated_date else None,
        'items': [
            {
                'ticker': item.ticker,
                'price_on_inception': item.price_on_inception,
                'added_at': item.added_at.isoformat() if item.added_at else None
            }
            for item in watchlist.items
        ]
    }

@with_transaction('user')
def add_watchlist(user_id: str, name: str, session=None):
    """Create a new watchlist for a user."""
    if not user_id:
        raise ValueError("User ID must be provided")
    if not name:
        raise ValueError("Name must be provided")

    watchlist = Watchlist(user_id=user_id, name=name, creation_date=get_current_utc_time())
    session.add(watchlist)
    session.flush()

    return {
        'id': str(watchlist.id),
        'user_id': str(watchlist.user_id),
        'name': watchlist.name,
        'creation_date': watchlist.creation_date.isoformat() if watchlist.creation_date else None
    }

@with_transaction('user')
def rename_watchlist(watchlist_id: str, name: str, session=None):
    """Rename an existing watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not name:
        raise ValueError("Name must be provided")

    watchlist = session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        return None

    watchlist.name = name
    watchlist.updated_date = get_current_utc_time()

    return {
        'id': str(watchlist.id),
        'name': watchlist.name,
        'updated_date': watchlist.updated_date.isoformat()
    }

@with_transaction('user')
def delete_watchlist(watchlist_id: str, session=None):
    """Delete a watchlist and all its items."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")

    watchlist = session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not watchlist:
        return False

    session.delete(watchlist)
    return True

@with_transaction('user')
def add_watchlist_item(watchlist_id: str, ticker: str, session=None):
    """Add a ticker to a watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not ticker:
        raise ValueError("Ticker must be provided")

    fmp = FMP_API_DATA()
    try:
        quote_data = fmp.get_full_quote(ticker)
        price_on_inception = quote_data[0]['price'] if quote_data else None
    except (IndexError, KeyError, Exception):
        price_on_inception = None

    watchlist_item = WatchlistItem(
        watchlist_id=watchlist_id,
        ticker=ticker.upper(),
        price_on_inception=price_on_inception,
        added_at=get_current_utc_time()
    )
    session.add(watchlist_item)
    session.flush()

    return {
        'watchlist_id': str(watchlist_item.watchlist_id),
        'ticker': watchlist_item.ticker,
        'price_on_inception': watchlist_item.price_on_inception,
        'added_at': watchlist_item.added_at.isoformat() if watchlist_item.added_at else None
    }

@with_transaction('user')
def delete_watchlist_item(watchlist_id: str, ticker: str, session=None):
    """Remove a ticker from a watchlist."""
    if not watchlist_id:
        raise ValueError("Watchlist ID must be provided")
    if not ticker:
        raise ValueError("Ticker must be provided")

    watchlist_item = session.query(WatchlistItem).filter(
        WatchlistItem.watchlist_id == watchlist_id,
        WatchlistItem.ticker == ticker.upper()
    ).first()

    if not watchlist_item:
        return False

    session.delete(watchlist_item)
    return True

