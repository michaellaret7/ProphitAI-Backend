"""User account repository — CRUD operations and broker account management."""

from app.db.core.models.user_data_models import *
from app.repositories.user.broker import get_snaptrade_broker, resolve_snaptrade_credentials
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List
from app.utils.decorators.database import with_session, with_transaction
from app.utils.time_utils import get_current_utc_time
import uuid


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

def _format_user_data(user) -> Dict[str, Any]:
    """Build the standard user response dict from a User ORM instance."""
    user_data = {
        'id': str(user.id),
        'clerk_id': user.clerk_id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'broker': user.broker,
        'snaptrade_account_id': user.snaptrade_account_id,
        'creation_date': user.creation_date.isoformat() if getattr(user, 'creation_date', None) else None,
        'portfolios': []
    }

    for portfolio in user.portfolios:
        user_data['portfolios'].append({
            'name': portfolio.name,
            'portfolio_id': str(portfolio.id),
            'nav': portfolio.nav,
            'is_current': portfolio.is_current,
            'is_discretionary': portfolio.is_discretionary
        })

    return user_data


# ════════════════════════════════════════════════════════════
# --> Read operations
# ════════════════════════════════════════════════════════════

@with_session('user')
def get_all_user_data(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get complete user data by email.

    Args:
        email: User's email address

    Returns:
        Dictionary containing complete user data with portfolios, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")

    user = session.query(User).options(
        selectinload(User.portfolios)
    ).filter(User.email == email).first()

    if not user:
        return None

    return _format_user_data(user)

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

    user = session.query(User).options(
        selectinload(User.portfolios)
    ).filter(User.id == user_id).first()

    if not user:
        return None

    return _format_user_data(user)

@with_session('user')
def get_all_user_data_by_clerk_id(clerk_id: str, session=None) -> Optional[Dict[str, Any]]:
    """Get complete user data by Clerk ID."""
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")

    user = session.query(User).options(
        selectinload(User.portfolios)
    ).filter(User.clerk_id == clerk_id).first()

    if not user:
        return None

    return _format_user_data(user)

@with_session('user')
def get_user_basic_info(email: str, session=None) -> Optional[Dict[str, Any]]:
    """
    Get basic user info (id, email, first_name, last_name) by email.

    Args:
        email: User's email address

    Returns:
        Dictionary containing only basic user info, or None if not found
    """
    if not email:
        raise ValueError("Email must be provided")

    user = session.query(User).filter(User.email == email).first()

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


# ════════════════════════════════════════════════════════════
# --> Write operations
# ════════════════════════════════════════════════════════════

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
def delete_user_by_clerk_id(clerk_id: str, session=None) -> bool:
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        return False
    session.delete(user)
    return True


# ════════════════════════════════════════════════════════════
# --> Broker Account Operations
# ════════════════════════════════════════════════════════════

@with_session('user')
def get_connection_status(clerk_id: str, session=None) -> Dict[str, Any]:
    """
    Check whether the user has SnapTrade credentials stored (DB-only, no API call).

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        Dict with registered (bool), connected (bool), account_id (str or None)
    """
    if not clerk_id:
        raise ValueError("Clerk ID must be provided")

    user = session.query(User).filter(User.clerk_id == clerk_id).first()

    if not user:
        return {"registered": False, "connected": False, "account_id": None}

    has_user_id = bool(user.snaptrade_user_id)
    has_account = bool(user.snaptrade_account_id)

    return {
        "registered": has_user_id,
        "connected": has_user_id and has_account,
        "account_id": user.snaptrade_account_id,
    }


def get_broker_account(clerk_id: str) -> Dict[str, Any]:
    """
    Get full broker account info via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        Dict with account details (number, name, type, status, balances, etc.)
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_account_details(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
    )


def get_balances(clerk_id: str) -> List[Dict[str, Any]]:
    """
    Get account balances (cash, buying power, equity) via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        List of balance dicts with currency, cash, buying_power fields
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_balances(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
    )


def _first_balance(clerk_id: str) -> Dict[str, Any]:
    """Return the first balance dict from SnapTrade, or empty dict."""
    balances = get_balances(clerk_id)
    return balances[0] if balances else {}


def get_equity(clerk_id: str) -> Optional[float]:
    """Get total account equity (balance total) via SnapTrade."""
    bal = _first_balance(clerk_id)
    return bal.get("amount") or bal.get("cash")


def get_buying_power(clerk_id: str) -> Optional[float]:
    """Get buying power from account balances via SnapTrade."""
    return _first_balance(clerk_id).get("buying_power")


def get_cash_balance(clerk_id: str) -> Optional[float]:
    """Get cash balance from account balances via SnapTrade."""
    return _first_balance(clerk_id).get("cash")


def get_account_activities(
    clerk_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
) -> list:
    """
    Get broker account activities (fills, dividends, transfers, etc.) via SnapTrade.

    Args:
        clerk_id: Clerk authentication ID
        start_date: Filter start date (YYYY-MM-DD)
        end_date: Filter end date (YYYY-MM-DD)
        activity_type: Filter by activity type

    Returns:
        List of activity dicts
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    broker = get_snaptrade_broker()
    return broker.get_account_activities(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        account_id=creds["snaptrade_account_id"],
        start_date=start_date,
        end_date=end_date,
        type=activity_type,
    )
