"""ProphitAI Shared — shared utilities for the ProphitAI platform."""

from prophitai_shared.time_utils import (
    get_current_utc_time,
    get_utc_days_ago,
    get_utc_date_range,
    get_utc_timestamp_str,
    get_utc_date_str,
    ensure_naive_utc,
)

from prophitai_shared.choose_model_and_client import (
    ProviderConfig,
    PROVIDER_CONFIGS,
    MODEL_ALIASES,
    get_model_and_client,
)

__all__ = [
    "get_current_utc_time",
    "get_utc_days_ago",
    "get_utc_date_range",
    "get_utc_timestamp_str",
    "get_utc_date_str",
    "ensure_naive_utc",
    "ProviderConfig",
    "PROVIDER_CONFIGS",
    "MODEL_ALIASES",
    "get_model_and_client",
]
