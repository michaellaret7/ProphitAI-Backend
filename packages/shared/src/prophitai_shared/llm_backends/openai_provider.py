"""OpenAI-compatible LLM provider."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from langfuse.openai import openai as langfuse_openai

from prophitai_shared.llm_backends.base import LLMBackend, T
from prophitai_shared.llm_backends.helpers.openai_helpers import (
    _normalize_openai_usage,
    _to_openai_messages,
)
from prophitai_shared.llm_backends.models import NormalizedLLMResponse, NormalizedToolCall


class OpenAICompatibleBackend(LLMBackend[T]):
    """Backend for OpenAI and OpenAI-compatible providers."""

    def __init__(self, *, provider: str, model: str, api_key: str, base_url: Optional[str] = None):
        client_kwargs: dict[str, Any] = {"api_key": api_key}

        if base_url:
            client_kwargs["base_url"] = base_url

        raw_client = langfuse_openai.OpenAI(**client_kwargs)

        super().__init__(
            provider=provider,
            model=model,
            raw_client=raw_client)

    def format_tools(self, tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format canonical tool definitions into OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
            for tool in tools
        ]

    def call_llm(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: Optional[Sequence[dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> NormalizedLLMResponse:
        """Send one OpenAI chat completion and normalize the response."""
        response = self.raw_client.chat.completions.create(
            model=self.model,
            messages=_to_openai_messages(messages),
            tools=self.format_tools(tools) if tools else None,
            tool_choice="auto" if tools else None,
            temperature=temperature,
        )

        message = response.choices[0].message
        tool_calls = [
            NormalizedToolCall(
                id=tool_call.id,
                name=tool_call.function.name,
                arguments_json=tool_call.function.arguments or "{}",
            )
            for tool_call in (message.tool_calls or [])
        ]

        return NormalizedLLMResponse(
            assistant_text=message.content or "",
            tool_calls=tool_calls,
            stop_reason=getattr(response.choices[0], "finish_reason", "") or "",
            usage=_normalize_openai_usage(getattr(response, "usage", None)),
            raw_response=response,
        )

    def call_llm_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        target_model: type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Return a validated Pydantic model via OpenAI structured output."""

        parse_method = type(self.raw_client.chat.completions).parse

        original_parse = getattr(parse_method, "__wrapped__", parse_method)

        completion = original_parse(
            self.raw_client.chat.completions,
            model=self.model,
            messages=_to_openai_messages(messages),
            response_format=target_model,
            temperature=temperature,
        )

        return completion.choices[0].message.parsed

    def call_llm_json(
        self,
        *,
        messages: list[dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> str:
        """Return a JSON object string via OpenAI json_object mode."""
        response = self.raw_client.chat.completions.create(
            model=self.model,
            messages=_to_openai_messages(messages),
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        return response.choices[0].message.content or "{}"
