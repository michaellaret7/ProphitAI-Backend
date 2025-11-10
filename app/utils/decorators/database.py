"""Database session management decorators.

These decorators remove repeated boilerplate for creating, committing/rolling back,
and closing SQLAlchemy sessions across the codebase.
"""

from functools import wraps
from typing import Any, Callable, Optional
import logging

from app.db.core.db_config import MarketSession, UserSession, ProphitAltsSession, MacroDataSession

logger = logging.getLogger(__name__)


def _get_session_class(session_type: str):
    mapping = {
        'market': MarketSession,
        'user': UserSession,
        'prophit': ProphitAltsSession,
        'macro': MacroDataSession,
    }
    try:
        return mapping[session_type]
    except KeyError:
        raise ValueError(f"Unsupported session_type '{session_type}'. Use 'market', 'user', 'prophit', or 'macro'.")


def with_session(session_type: str = 'market') -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that injects and manages a database session.

    - Creates the requested session type if one is not provided
    - Passes it to the wrapped function via the 'session' kwarg
    - Ensures the session is closed after the function completes

    If a 'session' kwarg is already provided, the decorator will not
    manage its lifecycle (no close/commit/rollback).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Respect externally provided session
            existing_session: Optional[Any] = kwargs.get('session')
            if existing_session is not None:
                return func(*args, **kwargs)

            session_cls = _get_session_class(session_type)
            session = session_cls()
            try:
                kwargs['session'] = session
                return func(*args, **kwargs)
            finally:
                try:
                    session.close()
                except Exception:
                    # Close should never raise, but guard just in case
                    logger.debug("Failed to close session cleanly", exc_info=True)

        return wrapper

    return decorator


def with_transaction(session_type: str = 'market') -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps function execution in a database transaction.

    - If no 'session' kwarg is provided, creates and manages one
    - Commits on success, rolls back on exception
    - Always closes the session it created

    If a 'session' kwarg is already provided, the decorator delegates
    transaction control to the caller and will not commit/rollback/close.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Respect externally provided session
            existing_session: Optional[Any] = kwargs.get('session')
            if existing_session is not None:
                return func(*args, **kwargs)

            session_cls = _get_session_class(session_type)
            session = session_cls()
            try:
                kwargs['session'] = session
                result = func(*args, **kwargs)
                session.commit()
                return result
            except Exception:
                try:
                    session.rollback()
                except Exception:
                    logger.debug("Failed to rollback session", exc_info=True)
                raise
            finally:
                try:
                    session.close()
                except Exception:
                    logger.debug("Failed to close session after transaction", exc_info=True)

        return wrapper

    return decorator


def with_sessions(**session_types) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that injects multiple named database sessions.
    
    Creates and manages multiple database sessions, injecting them as named parameters.
    Each session is automatically closed after function execution.
    
    Usage:
        @with_sessions(user_session='user', market_session='market')
        def my_func(user_session=None, market_session=None):
            user_session.query(User)...
            market_session.query(Ticker)...
    
    Args:
        **session_types: Keyword arguments where key is the parameter name
                        and value is the session type ('market', 'user', or 'prophit')
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            sessions = {}
            try:
                # Create sessions for any that weren't provided
                for param_name, session_type in session_types.items():
                    if kwargs.get(param_name) is None:
                        session_cls = _get_session_class(session_type)
                        sessions[param_name] = session_cls()
                        kwargs[param_name] = sessions[param_name]
                
                return func(*args, **kwargs)
            finally:
                # Close all sessions we created
                for session in sessions.values():
                    try:
                        session.close()
                    except Exception:
                        logger.debug("Failed to close session cleanly", exc_info=True)
        
        return wrapper
    
    return decorator


