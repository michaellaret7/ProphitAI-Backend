"""Shared helpers for broker agent tools."""


def resolve_user_id_by_email(email: str) -> str:
    """Resolve an email address to the internal user UUID string.

    Args:
        email: User email address.

    Raises:
        ValueError: If user not found.
    """
    from app.utils.decorators.database import with_session
    from app.db.core.models.user_data_models import User

    @with_session('user')
    def _query(*, session=None) -> str:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError(f"User not found for email: {email}")
        return str(user.id)

    return _query()
