"""Shared helpers for broker agent tools."""

from typing import Optional


# ================================
# --> Helper funcs
# ================================

_NO_BROKER_MSG = (
    "No brokerage account is connected. Connect a broker in your "
    "account settings to enable trading, positions, and order management."
)


def check_broker_connected(clerk_id: str) -> Optional[str]:
    """Check whether the user has a connected brokerage account.

    Args:
        clerk_id: Clerk authentication ID.

    Returns:
        None if broker is connected, user-friendly message string if not.
    """
    from prophitai_data.clients.snaptrade import resolve_snaptrade_credentials

    try:
        resolve_snaptrade_credentials(clerk_id=clerk_id)
        return None
    except (ValueError, Exception):
        return _NO_BROKER_MSG


def resolve_user_id_by_clerk_id(clerk_id: str) -> str:
    """Resolve a Clerk ID to the internal user UUID string.

    Args:
        clerk_id: Clerk authentication ID.

    Raises:
        ValueError: If user not found.
    """
    from prophitai_data.session import with_session
    from prophitai_data.db.models.user import User

    @with_session('user')
    def _query(*, session=None) -> str:
        user = session.query(User).filter(User.clerk_id == clerk_id).first()
        if not user:
            raise ValueError(f"User not found for clerk_id: {clerk_id}")
        return str(user.id)

    return _query()
