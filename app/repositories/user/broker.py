"""Lazy SnapTrade broker singleton and credential resolver."""

from typing import Dict, Optional
from app.utils.decorators.database import with_session, with_transaction
from app.db.core.models.user_data_models import User


# ════════════════════════════════════════════════════════════
# --> Helper funcs
# ════════════════════════════════════════════════════════════

_snaptrade_instance = None


def _fetch_and_persist_account_id(*, user_id: str, user_secret: str, clerk_id: str) -> str:
    """
    Fetch linked accounts from SnapTrade and persist the first account ID.

    Called automatically when a user has auth credentials but no account_id,
    meaning OAuth completed but the callback was never triggered.

    Returns:
        The snaptrade_account_id string

    Raises:
        ValueError: If no accounts found on SnapTrade
    """
    st_broker = get_snaptrade_broker()
    accounts = st_broker.list_accounts(user_id=user_id, user_secret=user_secret)

    if not accounts:
        raise ValueError("No brokerage accounts found — complete OAuth connection first")

    account_id = accounts[0]["id"]
    _persist_account_id(clerk_id=clerk_id, account_id=account_id)
    return account_id


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
    If the user has auth credentials but no account_id, automatically
    fetches and persists it from SnapTrade.

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

    if not user.snaptrade_user_id or not user.snaptrade_user_secret:
        raise ValueError("User is missing SnapTrade authentication credentials")

    # Reason: Auto-fetch account_id if user completed OAuth but callback was never triggered
    if not user.snaptrade_account_id:
        account_id = _fetch_and_persist_account_id(
            user_id=user.snaptrade_user_id,
            user_secret=user.snaptrade_user_secret,
            clerk_id=user.clerk_id,
        )
        user.snaptrade_account_id = account_id

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


@with_session('user')
def resolve_snaptrade_auth(
    *,
    clerk_id: Optional[str] = None,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    session=None,
) -> Dict[str, str]:
    """
    Resolve user identifier to snaptrade_user_id + snaptrade_user_secret.

    Lighter version of resolve_snaptrade_credentials — does NOT require
    snaptrade_account_id, so it can be used during the connection flow
    before OAuth completes.

    Returns:
        Dict with snaptrade_user_id and snaptrade_user_secret

    Raises:
        ValueError: If no identifier provided, user not found, or missing auth credentials
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

    if not user.snaptrade_user_id or not user.snaptrade_user_secret:
        raise ValueError("User is missing SnapTrade authentication credentials")

    return {
        "snaptrade_user_id": user.snaptrade_user_id,
        "snaptrade_user_secret": user.snaptrade_user_secret,
    }


@with_transaction('user')
def register_snaptrade_user(*, clerk_id: str, session=None) -> Dict[str, str]:
    """
    Register a new user with SnapTrade and persist credentials.

    Calls SnapTrade's register_user endpoint, then stores the returned
    userId and userSecret on the User row.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        Dict with snaptrade_user_id and snaptrade_user_secret

    Raises:
        ValueError: If user not found or already registered
    """
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        raise ValueError("User not found")

    if user.snaptrade_user_id:
        raise ValueError("User is already registered with SnapTrade")

    st_broker = get_snaptrade_broker()
    result = st_broker.register_user(user_id=clerk_id)

    user.snaptrade_user_id = result["userId"]
    user.snaptrade_user_secret = result["userSecret"]

    return {
        "snaptrade_user_id": user.snaptrade_user_id,
        "snaptrade_user_secret": user.snaptrade_user_secret,
    }


def save_snaptrade_account(*, clerk_id: str) -> Dict[str, str]:
    """
    Fetch linked accounts from SnapTrade after OAuth and persist the account ID.

    Resolves user auth credentials, calls list_accounts, and stores the
    first account's ID on the User row.

    Args:
        clerk_id: Clerk authentication ID

    Returns:
        Dict with snaptrade_account_id

    Raises:
        ValueError: If no accounts found after OAuth
    """
    creds = resolve_snaptrade_auth(clerk_id=clerk_id)
    st_broker = get_snaptrade_broker()

    accounts = st_broker.list_accounts(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
    )

    if not accounts:
        raise ValueError("No brokerage accounts found — OAuth may not have completed")

    account_id = accounts[0]["id"]
    _persist_account_id(clerk_id=clerk_id, account_id=account_id)

    return {"snaptrade_account_id": account_id}


@with_transaction('user')
def _persist_account_id(*, clerk_id: str, account_id: str, session=None) -> None:
    """Persist a SnapTrade account ID on the User row."""
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        raise ValueError("User not found")
    user.snaptrade_account_id = account_id


def get_snaptrade_connect_url(
    *,
    clerk_id: str,
    broker: Optional[str] = None,
    custom_redirect: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate a SnapTrade connection portal redirect URL for a user.

    Resolves the user's SnapTrade credentials from the DB, then calls
    SnapTrade's login endpoint to produce a one-time redirect URI.
    Always connects with trade permissions.

    Args:
        clerk_id: Clerk authentication ID
        broker: Pre-select a specific brokerage (e.g. 'ALPACA', 'INTERACTIVE_BROKERS')
        custom_redirect: URL to redirect after connection

    Returns:
        Dict with 'redirectURI'
    """
    creds = resolve_snaptrade_auth(clerk_id=clerk_id)
    st_broker = get_snaptrade_broker()

    # Reason: Always force trade permissions — never allow read-only connections
    result = st_broker.login_user(
        user_id=creds["snaptrade_user_id"],
        user_secret=creds["snaptrade_user_secret"],
        broker=broker,
        connection_type="trade",
        custom_redirect=custom_redirect,
    )
    return {"redirectURI": result["redirectURI"]}
