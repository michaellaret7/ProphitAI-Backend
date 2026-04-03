"""OpenAI-specific helper functions for message conversion and usage normalization."""

from __future__ import annotations

from typing import Any

from prophitai_shared.llm_backends.models import UsageStats


def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert internal message format to OpenAI wire format."""
    openai_messages: list[dict[str, Any]] = []
    for message in messages:
        role = message["role"]
        if role == "assistant" and message.get("tool_calls"):
            openai_messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": [
                        tool_call.to_openai_dict()
                        for tool_call in message.get("tool_calls", [])
                    ],
                }
            )
            continue

        if role == "tool":
            openai_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": message["tool_call_id"],
                    "content": message.get("content") or "",
                }
            )
            continue

        openai_messages.append(
            {
                "role": role,
                "content": message.get("content") or "",
            }
        )
    return openai_messages


def _normalize_openai_usage(usage: Any) -> UsageStats:
    """Normalize OpenAI usage stats into UsageStats."""
    if usage is None:
        return UsageStats()

    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)
    prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
    cache_read_input_tokens = int(getattr(prompt_tokens_details, "cached_tokens", 0) or 0)

    return UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )
