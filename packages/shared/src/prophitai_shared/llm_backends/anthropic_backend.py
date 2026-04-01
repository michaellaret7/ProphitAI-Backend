"""Anthropic Messages API backend."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Optional, Sequence

from anthropic import Anthropic

from prophitai_shared.llm_backends.base import DEFAULT_MAX_OUTPUT_TOKENS, LLMBackend, T
from prophitai_shared.llm_backends.models import NormalizedLLMResponse, NormalizedToolCall, UsageStats
from prophitai_shared.llm_backends.utils import _compact_kwargs, _strip_json_wrappers

ANTHROPIC_PROMPT_CACHE_ENABLED = (
    os.getenv("USE_ANTHROPIC_PROMPT_CACHING", "true").strip().lower() in {"1", "true", "yes", "on"}
)
ANTHROPIC_CACHE_CONTROL = {"type": "ephemeral"}
_ANTHROPIC_OTEL_LOCK = threading.Lock()
_ANTHROPIC_OTEL_INSTRUMENTED = False


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
            content = message.get("content") or ""
            if content:
                system_blocks.append(_build_anthropic_text_block(content, cacheable=False))
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

    if ANTHROPIC_PROMPT_CACHE_ENABLED and system_blocks:
        system_blocks[-1]["cache_control"] = dict(ANTHROPIC_CACHE_CONTROL)

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


def _build_anthropic_text_block(text: str, *, cacheable: bool) -> dict[str, Any]:
    """Build an Anthropic text block, optionally with cache control."""
    block = {"type": "text", "text": text}
    if cacheable and ANTHROPIC_PROMPT_CACHE_ENABLED:
        block["cache_control"] = dict(ANTHROPIC_CACHE_CONTROL)
    return block


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


# ================================
# --> Anthropic Backend
# ================================


class AnthropicBackend(LLMBackend[T]):
    """Backend for native Anthropic Messages API."""

    def __init__(self, *, model: str, api_key: str):
        _ensure_anthropic_instrumentation()
        raw_client = Anthropic(api_key=api_key)
        super().__init__(
            provider="anthropic", 
            model=model, 
            raw_client=raw_client
        )

    def render_tools(self, tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Render canonical tool definitions into Anthropic tool format."""
        rendered_tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            }
            for tool in tools
        ]
        if ANTHROPIC_PROMPT_CACHE_ENABLED and rendered_tools:
            rendered_tools[-1]["cache_control"] = dict(ANTHROPIC_CACHE_CONTROL)
        return rendered_tools

    def create_turn(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: Optional[Sequence[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> NormalizedLLMResponse:
        """Send one Anthropic message turn and normalize the response."""
        system_blocks, anthropic_messages = _to_anthropic_messages(messages)
        response = self.raw_client.messages.create(
            **_compact_kwargs(
                model=self.model,
                system=system_blocks or None,
                messages=anthropic_messages,
                tools=self.render_tools(tools) if tools else None,
                temperature=temperature,
                max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            )
        )

        assistant_text = []
        tool_calls: list[NormalizedToolCall] = []

        for block in response.content:
            if block.type == "text":
                assistant_text.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    NormalizedToolCall(
                        id=block.id,
                        name=block.name,
                        arguments_json=json.dumps(block.input or {}, ensure_ascii=True),
                    )
                )

        return NormalizedLLMResponse(
            assistant_text="".join(assistant_text).strip(),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "",
            usage=_normalize_anthropic_usage(getattr(response, "usage", None)),
            raw_response=response,
        )

    def parse_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        target_model: type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Return a validated Pydantic model via Anthropic JSON extraction."""
        schema_json = json.dumps(target_model.model_json_schema(), ensure_ascii=True)
        json_text = self._create_json_with_instruction(
            messages=messages,
            instruction=(
                "Return only valid JSON matching this schema exactly. "
                "Do not include markdown fences or explanatory text.\n"
                f"{schema_json}"
            ),
            temperature=temperature,
        )
        return target_model.model_validate_json(json_text)

    def create_json_object(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> str:
        """Return a JSON object string via Anthropic."""
        return self._create_json_with_instruction(
            messages=messages,
            instruction=(
                "Return only a valid JSON object. "
                "Do not include markdown fences or any explanatory text."
            ),
            temperature=temperature,
        )

    def _create_json_with_instruction(
        self,
        *,
        messages: list[dict[str, Any]],
        instruction: str,
        temperature: Optional[float] = None,
    ) -> str:
        """Send a message with a JSON instruction appended to system blocks."""
        system_blocks, anthropic_messages = _to_anthropic_messages(messages)
        if instruction:
            system_blocks = [
                *system_blocks,
                _build_anthropic_text_block(instruction, cacheable=True),
            ]
        response = self.raw_client.messages.create(
            **_compact_kwargs(
                model=self.model,
                system=system_blocks or None,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            )
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return _strip_json_wrappers(text)
