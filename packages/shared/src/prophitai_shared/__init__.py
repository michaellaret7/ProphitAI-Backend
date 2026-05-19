"""ProphitAI Shared - shared utilities for the ProphitAI platform."""

from prophitai_shared.time_utils import (
    ensure_naive_utc,
    get_current_utc_time,
    get_utc_date_range,
    get_utc_date_str,
    get_utc_days_ago,
    get_utc_timestamp_str,
)

from prophitai_shared.client import build_client
from prophitai_shared.messages import (
    assistant_msg,
    cached_text,
    refresh_rolling_cache_breakpoint,
    system_msg,
    tool_msg,
    user_msg,
)
from prophitai_shared.usage import Usage

__all__ = [
    "get_current_utc_time",
    "get_utc_days_ago",
    "get_utc_date_range",
    "get_utc_timestamp_str",
    "get_utc_date_str",
    "ensure_naive_utc",
    "build_client",
    "system_msg",
    "user_msg",
    "assistant_msg",
    "tool_msg",
    "cached_text",
    "refresh_rolling_cache_breakpoint",
    "Usage",
]
