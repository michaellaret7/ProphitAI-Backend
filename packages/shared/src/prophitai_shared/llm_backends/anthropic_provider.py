"""Anthropic Messages API provider."""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

from anthropic import Anthropic

from prophitai_shared.llm_backends.base import LLMBackend, T
from prophitai_shared.llm_backends.helpers.anthropic_helpers import (
    ANTHROPIC_CACHE_POLICY,
    _build_anthropic_text_block,
    _ensure_anthropic_instrumentation,
    _normalize_anthropic_usage,
    _to_anthropic_messages,
)
from prophitai_shared.llm_backends.models import NormalizedLLMResponse, NormalizedToolCall
from prophitai_shared.llm_backends.utils import _compact_kwargs, _strip_json_wrappers


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

    def format_tools(self, tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format canonical tool definitions into Anthropic tool format."""
        rendered_tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            }
            for tool in tools
        ]
        if ANTHROPIC_CACHE_POLICY.enabled and ANTHROPIC_CACHE_POLICY.cache_tools and rendered_tools:
            rendered_tools[-1]["cache_control"] = dict(ANTHROPIC_CACHE_POLICY.cache_control)
        return rendered_tools

    def call_llm(
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
                cache_control=(
                    dict(ANTHROPIC_CACHE_POLICY.cache_control)
                    if ANTHROPIC_CACHE_POLICY.enabled and ANTHROPIC_CACHE_POLICY.automatic_conversation_caching
                    else None
                ),
                system=system_blocks or None,
                messages=anthropic_messages,
                tools=self.format_tools(tools) if tools else None,
                temperature=temperature,
                thinking={"type": "adaptive"},
                max_tokens=64000,
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

    def call_llm_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        target_model: type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Return a validated Pydantic model via Anthropic native structured output."""
        system_blocks, anthropic_messages = _to_anthropic_messages(messages)

        response = self.raw_client.messages.parse(
            **_compact_kwargs(
                model=self.model,
                system=system_blocks or None,
                messages=anthropic_messages,
                output_format=target_model,
                temperature=temperature,
                max_tokens=64000,
            )
        )
        return response.parsed_output

    def call_llm_json(
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
                max_tokens=64000,
            )
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return _strip_json_wrappers(text)
