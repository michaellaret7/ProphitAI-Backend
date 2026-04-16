"""Anthropic-specific helper functions for message conversion, caching, and instrumentation."""

from __future__ import annotations

import os
import threading
from typing import Any

from prophitai_shared.llm_backends.models import UsageStats

_ANTHROPIC_OTEL_LOCK = threading.Lock()
_ANTHROPIC_OTEL_INSTRUMENTED = False

ANTHROPIC_CACHING_ENABLED: bool = os.getenv(
    "USE_ANTHROPIC_PROMPT_CACHING", "true"
).strip().lower() in {"1", "true", "yes", "on"}

CACHE_CONTROL_EPHEMERAL: dict[str, str] = {"type": "ephemeral"}


# ================================
# --> Helper funcs
# ================================


def _to_anthropic_messages(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert internal message format to Anthropic system blocks + messages."""
    system_blocks: list[dict[str, Any]] = []
    anthropic_messages: list[dict[str, Any]] = []
    pending_tool_results: list[dict[str, Any]] = []

    for message in messages:
        role = message["role"]

        if role == "system":
            system_blocks.extend(_coerce_system_blocks(message.get("content")))
            continue

        if role == "tool":
            pending_tool_results.append(message)
            continue

        if pending_tool_results:
            anthropic_messages.append(_build_anthropic_tool_result_message(pending_tool_results))
            pending_tool_results = []

        if role == "user":
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": _ensure_anthropic_text_blocks(message.get("content") or ""),
                }
            )
            continue

        if role == "assistant":
            content_blocks: list[dict[str, Any]] = []
            text = message.get("content") or ""
            if text:
                content_blocks.append({"type": "text", "text": text})

            for tool_call in message.get("tool_calls", []):
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "input": tool_call.parsed_arguments(),
                    }
                )

            if content_blocks:
                anthropic_messages.append({"role": "assistant", "content": content_blocks})

    if pending_tool_results:
        anthropic_messages.append(_build_anthropic_tool_result_message(pending_tool_results))

    _ensure_system_cache_breakpoint(system_blocks)

    return system_blocks, anthropic_messages


def _build_anthropic_tool_result_message(tool_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an Anthropic user message containing tool_result blocks."""

    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": message["tool_call_id"],
                "content": message.get("content") or "",
            }
            for message in tool_messages
        ],
    }


def _ensure_anthropic_text_blocks(content: Any) -> list[dict[str, Any]]:
    """Ensure content is a list of Anthropic text blocks."""
    if isinstance(content, list):
        return content
    return [{"type": "text", "text": str(content)}]


def _coerce_system_blocks(content: Any) -> list[dict[str, Any]]:
    """Convert internal system content into Anthropic text blocks."""
    if not content:
        return []

    if isinstance(content, str):
        return [_build_anthropic_text_block(content, cacheable=False)]

    if isinstance(content, list):
        blocks: list[dict[str, Any]] = []
        for block in content:
            if isinstance(block, str):
                blocks.append(_build_anthropic_text_block(block, cacheable=False))
                continue

            if not isinstance(block, dict):
                blocks.append(_build_anthropic_text_block(str(block), cacheable=False))
                continue

            if "cache_control" in block:
                normalized = dict(block)
                normalized.pop("cacheable", None)
                blocks.append(normalized)
                continue

            block_text = block.get("text")
            if block_text is None:
                blocks.append(_build_anthropic_text_block(str(block), cacheable=False))
                continue

            blocks.append(
                _build_anthropic_text_block(
                    str(block_text),
                    cacheable=bool(block.get("cacheable", False)),
                )
            )
        return blocks

    return [_build_anthropic_text_block(str(content), cacheable=False)]


def _build_anthropic_text_block(text: str, *, cacheable: bool) -> dict[str, Any]:
    """Build an Anthropic text block, optionally with cache control."""
    block = {"type": "text", "text": text}

    if cacheable and ANTHROPIC_CACHING_ENABLED:
        block["cache_control"] = dict(CACHE_CONTROL_EPHEMERAL)

    return block


def _ensure_system_cache_breakpoint(system_blocks: list[dict[str, Any]]) -> None:
    """Ensure there is one explicit static-system cache breakpoint when none was supplied."""
    if not system_blocks or not ANTHROPIC_CACHING_ENABLED:
        return

    if any("cache_control" in block for block in system_blocks):
        return

    system_blocks[-1]["cache_control"] = dict(CACHE_CONTROL_EPHEMERAL)


def _normalize_anthropic_usage(usage: Any) -> UsageStats:
    """Normalize Anthropic usage stats into UsageStats."""
    if usage is None:
        return UsageStats()

    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cache_creation_input_tokens = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    cache_read_input_tokens = int(getattr(usage, "cache_read_input_tokens", 0) or 0)

    return UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
    )


def _ensure_anthropic_instrumentation() -> None:
    """Instrument the Anthropic SDK once for Langfuse/OpenTelemetry tracing."""
    global _ANTHROPIC_OTEL_INSTRUMENTED

    if _ANTHROPIC_OTEL_INSTRUMENTED:
        return

    with _ANTHROPIC_OTEL_LOCK:
        if _ANTHROPIC_OTEL_INSTRUMENTED:
            return

        try:
            from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

            instrumentor = AnthropicInstrumentor()
            if not instrumentor.is_instrumented_by_opentelemetry:
                instrumentor.instrument()
            _ANTHROPIC_OTEL_INSTRUMENTED = True
        except Exception:
            # Reason: tracing must never block Anthropic model calls.
            _ANTHROPIC_OTEL_INSTRUMENTED = False
