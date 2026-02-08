"""User CRUD repository functions for creating, reading, updating, and deleting user records."""

from app.db.core.db_config import UserSession
from app.db.core.models.user_data_models import *
from sqlalchemy.orm import joinedload, selectinload
from typing import Optional, Dict, Any
from app.utils.decorators.database import with_session, with_transaction
from app.utils.time_utils import get_current_utc_time
import uuid


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
        'role': user.role,
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
            'nav': portfolio.nav,
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
        'role': user.role,
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
            'nav': portfolio.nav,
            'is_current': portfolio.is_current,
            'is_discretionary': portfolio.is_discretionary
        })
    return user_data

@with_session('user')
def get_all_ria_client_portfolios_by_id(user_id: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get all client portfolios for a RIA by internal user ID (UUID).

    Args:
        user_id: Internal database RIA user UUID

    Returns:
        Dictionary containing all client portfolios for the RIA, or None if not found
    """
    if not user_id:
        raise ValueError("User ID must be provided")

    user = session.query(User).options(
        joinedload(User.company),
        selectinload(User.portfolios)
    ).filter(User.id == user_id).first()

    if not user:
        return None

    # Reason: RIAs don't have their own portfolios — they manage client portfolios
    if user.role == 'ria':
        portfolios = session.query(Portfolio).join(
            User, Portfolio.user_id == User.id
        ).filter(User.handler_id == user.id).all()
    else:
        portfolios = user.portfolios

    user_data = {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
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
    for portfolio in portfolios:
        user_data['portfolios'].append({
            'name': portfolio.name,
            'portfolio_id': str(portfolio.id),
            'user_id': str(portfolio.user_id),
            'nav': portfolio.nav,
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
        'role': user.role,
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
            'nav': portfolio.nav,
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

VALID_USER_ROLES = {'ria', 'client', 'individual'}

@with_transaction('user')
def set_user_role_by_clerk_id(clerk_id: str, role: str, session=None) -> bool:
    """
    Set user role during onboarding. Only allowed when role is currently unset.

    Args:
        clerk_id: Clerk user ID
        role: One of 'ria', 'client', 'individual'

    Returns:
        True if role was set, False if user not found

    Raises:
        ValueError: If role is invalid or already set
    """
    if role not in VALID_USER_ROLES:
        raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(VALID_USER_ROLES)}")

    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        return False

    if user.role is not None:
        raise ValueError("Role has already been set")

    user.role = role
    return True


@with_transaction('user')
def delete_user_by_clerk_id(clerk_id: str, session=None) -> bool:
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        return False
    session.delete(user)
    return True
