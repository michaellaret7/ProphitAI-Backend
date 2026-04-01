"""OpenAI-compatible LLM backend."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from langfuse.openai import openai as langfuse_openai

from prophitai_shared.llm_backends.base import LLMBackend, T
from prophitai_shared.llm_backends.models import NormalizedLLMResponse, NormalizedToolCall, UsageStats


# ================================
# --> Helper funcs
# ================================


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


# ================================
# --> OpenAI Backend
# ================================


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

    def render_tools(self, tools: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Render canonical tool definitions into OpenAI function-calling format."""
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

    def create_turn(
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
            tools=self.render_tools(tools) if tools else None,
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

    def parse_structured(
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

    def create_json_object(
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
