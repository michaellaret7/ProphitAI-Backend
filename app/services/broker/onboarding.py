"""Broker onboarding services — SnapTrade user registration and connection."""

import uuid
from typing import Optional, Dict, Any

from app.repositories.user.broker import (
    get_snaptrade_broker,
    resolve_snaptrade_auth,
    _persist_account_id,
)
from app.utils.decorators.database import with_transaction
from app.utils.time_utils import get_current_utc_time
from app.db.core.models.user_data_models import User


# ════════════════════════════════════════════════════════════
# --> Onboarding
# ════════════════════════════════════════════════════════════

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
        # Reason: JIT provisioning — covers local dev where Clerk webhooks can't reach localhost
        from app.api.auth.clerk import get_clerk_client
        clerk = get_clerk_client()
        clerk_user = clerk.users.get(user_id=clerk_id)
        email = clerk_user.email_addresses[0].email_address
        user = User(
            id=uuid.uuid4(),
            email=email,
            first_name=clerk_user.first_name or "",
            last_name=clerk_user.last_name or "",
            clerk_id=clerk_id,
            creation_date=get_current_utc_time(),
        )
        session.add(user)
        session.flush()

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
