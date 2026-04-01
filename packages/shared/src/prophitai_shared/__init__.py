"""ProphitAI Shared - shared utilities for the ProphitAI platform."""

from prophitai_shared.time_utils import (
    ensure_naive_utc,
    get_current_utc_time,
    get_utc_date_range,
    get_utc_date_str,
    get_utc_days_ago,
    get_utc_timestamp_str,
)

from prophitai_shared.choose_model_and_client import (
    MODEL_ALIASES,
    PROVIDER_CONFIGS,
    ProviderConfig,
    get_backend,
)
from prophitai_shared.llm_backends import (
    AnthropicBackend,
    LLMBackend,
    NormalizedLLMResponse,
    NormalizedToolCall,
    OpenAICompatibleBackend,
    UsageStats,
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
    "LLMBackend",
    "OpenAICompatibleBackend",
    "AnthropicBackend",
    "NormalizedLLMResponse",
    "NormalizedToolCall",
    "UsageStats",
    "get_backend",
]
