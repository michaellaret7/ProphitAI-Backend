"""Lazy ProphitBroker singleton and clerk_id → broker_account_id resolver."""

from typing import Optional
from app.utils.decorators.database import with_session
from app.db.core.models.user_data_models import User


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

_broker_instance = None


def get_broker():
    """
    Return a lazy-initialised ProphitBroker singleton.

    Avoids import-time side effects (HTTP client init, env var reads)
    by deferring construction until first call.
    """
    global _broker_instance
    if _broker_instance is None:
        from app.brokers.alpaca_broker import ProphitBroker
        _broker_instance = ProphitBroker(sandbox=True)
    return _broker_instance


@with_session('user')
def resolve_broker_account(
    *,
    clerk_id: Optional[str] = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    session=None,
) -> str:
    """
    Resolve any user identifier to a broker_account_id.

    Accepts exactly one of clerk_id, user_id, or email.
    Queries the User table and returns the broker_account_id string.

    Args:
        clerk_id: Clerk authentication ID
        user_id: Internal database UUID
        email: User email address

    Returns:
        broker_account_id string

    Raises:
        ValueError: If no identifier provided, user not found, or user has no broker account
    """
    if not any([clerk_id, user_id, email]):
        raise ValueError("At least one identifier (clerk_id, user_id, email) must be provided")

    if clerk_id:
        user = session.query(User).filter(User.clerk_id == clerk_id).first()
    elif user_id:
        user = session.query(User).filter(User.id == user_id).first()
    else:
        user = session.query(User).filter(User.email == email).first()

    if not user:
        raise ValueError("User not found")

    if not user.broker_account_id:
        raise ValueError("User has no broker account")

    return user.broker_account_id
