"""Lazy SnapTrade broker singleton and credential resolver."""

from typing import Dict, Optional
from app.utils.decorators.database import with_session
from app.db.core.models.user_data_models import User


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

_snaptrade_instance = None


def get_snaptrade_broker():
    """
    Return a lazy-initialised SnapTradeBroker singleton.

    Credentials (client_id, consumer_key) are read from env vars
    inside SnapTradeClient on first call.
    """
    global _snaptrade_instance
    if _snaptrade_instance is None:
        from app.brokers.snaptrade.broker import SnapTradeBroker
        _snaptrade_instance = SnapTradeBroker()
    return _snaptrade_instance


@with_session('user')
def resolve_snaptrade_credentials(
    *,
    clerk_id: Optional[str] = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    session=None,
) -> Dict[str, str]:
    """
    Resolve any user identifier to all three SnapTrade credential fields.

    Accepts exactly one of clerk_id, user_id, or email.

    Args:
        clerk_id: Clerk authentication ID
        user_id: Internal database UUID
        email: User email address

    Returns:
        Dict with snaptrade_user_id, snaptrade_user_secret, snaptrade_account_id

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

    if not user.snaptrade_account_id:
        raise ValueError("User has no broker account")

    if not user.snaptrade_user_id or not user.snaptrade_user_secret:
        raise ValueError("User is missing SnapTrade authentication credentials")

    return {
        "snaptrade_user_id": user.snaptrade_user_id,
        "snaptrade_user_secret": user.snaptrade_user_secret,
        "snaptrade_account_id": user.snaptrade_account_id,
    }


def resolve_broker_account(
    *,
    clerk_id: Optional[str] = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
) -> str:
    """
    Resolve any user identifier to a snaptrade_account_id string.

    Thin wrapper around resolve_snaptrade_credentials for callers
    that only need the account ID (trading, funding, portfolio repos).

    Args:
        clerk_id: Clerk authentication ID
        user_id: Internal database UUID
        email: User email address

    Returns:
        snaptrade_account_id string

    Raises:
        ValueError: If no identifier provided, user not found, or user has no broker account
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id, user_id=user_id, email=email)
    return creds["snaptrade_account_id"]


def get_snaptrade_connect_url(
    *,
    clerk_id: str,
    broker: Optional[str] = None,
    connection_type: Optional[str] = None,
    custom_redirect: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate a SnapTrade connection portal redirect URL for a user.

    Resolves the user's SnapTrade credentials from the DB, then calls
    SnapTrade's login endpoint to produce a one-time redirect URI.

    Args:
        clerk_id: Clerk authentication ID
        broker: Pre-select a specific brokerage (e.g. 'ALPACA', 'INTERACTIVE_BROKERS')
        connection_type: Filter connection type ('read', 'trade')
        custom_redirect: URL to redirect after connection

    Returns:
        Dict with 'redirectURI'
    """
    creds = resolve_snaptrade_credentials(clerk_id=clerk_id)
    st_broker = get_snaptrade_broker()

    result = st_broker.login_user(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        broker=broker,
        connection_type=connection_type,
        custom_redirect=custom_redirect,
    )
    return {"redirectURI": result["redirectURI"]}
