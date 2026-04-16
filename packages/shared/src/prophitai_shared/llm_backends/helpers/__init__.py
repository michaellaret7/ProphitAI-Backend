"""Helper functions for LLM backend implementations."""

from prophitai_shared.llm_backends.helpers.anthropic_helpers import (
    ANTHROPIC_CACHING_ENABLED,
    CACHE_CONTROL_EPHEMERAL,
    _build_anthropic_text_block,
    _build_anthropic_tool_result_message,
    _coerce_system_blocks,
    _ensure_anthropic_instrumentation,
    _ensure_anthropic_text_blocks,
    _ensure_system_cache_breakpoint,
    _normalize_anthropic_usage,
    _to_anthropic_messages,
)
from prophitai_shared.llm_backends.helpers.openai_helpers import (
    _normalize_openai_usage,
    _to_openai_messages,
)

__all__ = [
    "ANTHROPIC_CACHING_ENABLED",
    "CACHE_CONTROL_EPHEMERAL",
    "_build_anthropic_text_block",
    "_build_anthropic_tool_result_message",
    "_coerce_system_blocks",
    "_ensure_anthropic_instrumentation",
    "_ensure_anthropic_text_blocks",
    "_ensure_system_cache_breakpoint",
    "_normalize_anthropic_usage",
    "_normalize_openai_usage",
    "_to_anthropic_messages",
    "_to_openai_messages",
]
