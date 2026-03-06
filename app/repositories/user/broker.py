"""Lazy SnapTrade broker singleton and credential resolver — pure DB access."""

from typing import Dict, Optional
from app.utils.decorators.database import with_session, with_transaction
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

    if not user.snaptrade_user_id or not user.snaptrade_user_secret:
        raise ValueError("User is missing SnapTrade authentication credentials")

    if not user.snaptrade_account_id:
        raise ValueError(
            "User is missing SnapTrade account ID — "
            "complete OAuth and call save_snaptrade_account first"
        )

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
def _persist_account_id(*, clerk_id: str, account_id: str, session=None) -> None:
    """Persist a SnapTrade account ID on the User row."""
    user = session.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        raise ValueError("User not found")
    user.snaptrade_account_id = account_id
