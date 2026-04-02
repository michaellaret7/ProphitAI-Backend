"""Normalized data models shared across LLM backends."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UsageStats:
    """Normalized usage stats across providers."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class NormalizedToolCall:
    """Provider-neutral representation of a tool call."""

    id: str
    name: str
    arguments_json: str = "{}"

    def parsed_arguments(self) -> dict[str, Any]:
        """Parse the JSON arguments string into a dictionary."""
        try:
            parsed = json.loads(self.arguments_json or "{}")
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def to_openai_dict(self) -> dict[str, Any]:
        """Convert to OpenAI wire format."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": self.arguments_json or "{}",
            },
        }


@dataclass
class NormalizedLLMResponse:
    """Provider-neutral LLM response consumed by the execution loop."""

    assistant_text: str
    tool_calls: list[NormalizedToolCall] = field(default_factory=list)
    stop_reason: str = ""
    usage: UsageStats = field(default_factory=UsageStats)
    raw_response: Any = None
