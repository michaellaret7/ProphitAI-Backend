"""Shared helpers for broker agent tools."""

from typing import Optional


# ================================
# --> Helper funcs
# ================================

_NO_BROKER_MSG = (
    "No brokerage account is connected. Connect a broker in your "
    "account settings to enable trading, positions, and order management."
)


def check_broker_connected(email: str) -> Optional[str]:
    """Check whether the user has a connected brokerage account.

    Args:
        email: User email address.

    Returns:
        None if broker is connected, user-friendly message string if not.
    """
    from prophitai_data.clients.snaptrade import resolve_snaptrade_credentials

    try:
        resolve_snaptrade_credentials(email=email)
        return None
    except (ValueError, Exception):
        return _NO_BROKER_MSG


def resolve_user_id_by_email(email: str) -> str:
    """Resolve an email address to the internal user UUID string.

    Args:
        email: User email address.

    Raises:
        ValueError: If user not found.
    """
    from prophitai_data.session import with_session
    from prophitai_data.db.models.user import User

    @with_session('user')
    def _query(*, session=None) -> str:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError(f"User not found for email: {email}")
        return str(user.id)

    return _query()
