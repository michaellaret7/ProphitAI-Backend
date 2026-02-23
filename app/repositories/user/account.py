"""User account repository — CRUD operations and broker account management."""

from app.db.core.models.user_data_models import *
from app.repositories.user.broker import get_broker, resolve_broker_account
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
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
        'broker_account_id': user.broker_account_id,
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

@with_transaction('user')
def create_user_with_broker_account(signup_data: Dict[str, Any], session=None) -> Dict[str, Any]:
    """
    Create a brokerage account on Alpaca and link it to a user record.

    If the user already exists (e.g. from Clerk webhook), the Alpaca account is
    created and linked to the existing row. If the user doesn't exist, both the
    user and Alpaca account are created.

    Alpaca runs KYC/AML automatically. On success, stores the returned
    account_id on the user row so every future broker call can resolve
    user -> account_id.

    Args:
        signup_data: Dict with:
            - first_name, last_name, email, phone
            - address, city, state, zip
            - dob (YYYY-MM-DD), ssn
            - funding_source (optional, defaults to 'employment_income')
            - clerk_id (optional)

    Returns:
        Dict with user_id, broker_account_id, account_status, and name
    """
    existing_user = session.query(User).filter(User.email == signup_data["email"]).first()

    if existing_user and existing_user.broker_account_id:
        raise ValueError(f"User with email {signup_data['email']} already has a broker account")

    # Reason: create Alpaca account first — if KYC fails we don't want an orphan DB row
    broker = get_broker()
    alpaca_result = broker.create_account(signup_data)

    if existing_user:
        # Reason: user exists from Clerk webhook — link the broker account
        existing_user.broker = "alpaca"
        existing_user.broker_account_id = alpaca_result["account_id"]
        user = existing_user
    else:
        user = User(
            id=uuid.uuid4(),
            email=signup_data["email"],
            first_name=signup_data["first_name"],
            last_name=signup_data["last_name"],
            clerk_id=signup_data.get("clerk_id"),
            broker="alpaca",
            broker_account_id=alpaca_result["account_id"],
            creation_date=get_current_utc_time(),
        )
        session.add(user)

    return {
        "user_id": str(user.id),
        "broker_account_id": alpaca_result["account_id"],
        "account_status": alpaca_result["status"],
        "name": alpaca_result["name"],
        "email": user.email,
    }


def get_broker_account(clerk_id: str) -> Dict:
    """Get full broker account info for a user."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_account(account_id)


def get_buying_power(clerk_id: str) -> float:
    """Get broker account buying power."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_buying_power(account_id)


def get_cash_balance(clerk_id: str) -> float:
    """Get broker account cash balance."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_cash(account_id)


def get_equity(clerk_id: str) -> float:
    """Get broker account equity."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_equity(account_id)


def get_account_activities(clerk_id: str, activity_type: Optional[str] = None) -> list:
    """Get broker account activities (fills, dividends, transfers, etc.)."""
    account_id = resolve_broker_account(clerk_id=clerk_id)
    return get_broker().get_account_activities(account_id, activity_type)
