"""
Centralized time utilities to ensure consistent UTC usage across the codebase.

All datetime operations should use these functions instead of datetime.now() to ensure
that we're always working with UTC times, which are then stored as naive datetimes
in the database for compatibility.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def get_current_utc_time() -> datetime:
    """
    Returns current UTC time as naive datetime for database compatibility.

    This function ensures all time operations use UTC consistently.
    The timezone info is stripped to maintain compatibility with our
    naive datetime database schema.

    Returns:
        datetime: Current UTC time without timezone info
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_utc_days_ago(days: int) -> datetime:
    """
    Returns UTC time N days ago as naive datetime.

    Args:
        days: Number of days to go back from current UTC time

    Returns:
        datetime: UTC time N days ago without timezone info
    """
    return get_current_utc_time() - timedelta(days=days)


def get_utc_date_range(lookback_days: int) -> tuple[datetime, datetime]:
    """
    Returns a date range from N days ago to current UTC time.

    Args:
        lookback_days: Number of days to look back

    Returns:
        tuple: (start_date, end_date) both as naive UTC datetimes
    """
    end_date = get_current_utc_time()
    start_date = end_date - timedelta(days=lookback_days)
    return start_date, end_date


def get_utc_timestamp_str() -> str:
    """
    Returns current UTC timestamp as ISO format string.
    Useful for logging and timestamping.

    Returns:
        str: Current UTC time in ISO format
    """
    return datetime.now(timezone.utc).isoformat()


def get_utc_date_str() -> str:
    """
    Returns current UTC date as YYYY-MM-DD string.

    Returns:
        str: Current UTC date
    """
    return get_current_utc_time().strftime('%Y-%m-%d')


def ensure_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensures a datetime is naive (no timezone info) for database storage.
    If the datetime has timezone info and is not UTC, it will be converted to UTC first.

    Args:
        dt: Datetime to process (can be None)

    Returns:
        datetime: Naive datetime in UTC, or None if input is None
    """
    if dt is None:
        return None

    if dt.tzinfo is not None:
        # Convert to UTC if it has timezone info
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        # Strip timezone info
        return dt.replace(tzinfo=None)

    # Already naive, assume it's UTC
    return dt
