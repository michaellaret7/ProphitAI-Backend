"""Smoke test for the OpenRouter client.

Verifies the full stack end-to-end:
- `build_client` returns a working OpenAI client + model slug.
- `system_msg(cache=True)` + `refresh_rolling_cache_breakpoint` produce a valid
  request that streams back tokens.
- An `Agent` with one tool can complete a turn that calls the tool and answers.

Run: `uv run python packages/shared/tests/test_openrouter_client.py`
"""

from __future__ import annotations

import os
import sys

# Reason: Windows console defaults to cp1252 which can't encode emojis the
# model may include in its answers. Switch stdout to utf-8 before any print.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode
from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response
from prophitai_shared import (
    Usage,
    build_client,
    refresh_rolling_cache_breakpoint,
    system_msg,
    user_msg,
)


# ================================
# --> Helper funcs
# ================================


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _require_env() -> None:
    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set in environment.")
        sys.exit(1)


# ================================
# --> Test 1: raw client streaming
# ================================


def test_raw_streaming_call() -> None:
    """Streams a hello-world completion through `build_client` directly."""
    _section("Test 1: raw streaming call via build_client")

    client, model = build_client("anthropic/claude-sonnet-4.6")

    messages = [
        system_msg("You are a concise assistant. Reply in one short sentence.", cache=True),
        user_msg("Say hello and confirm you're alive."),
    ]

    refresh_rolling_cache_breakpoint(messages)

    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=True,
        stream_options={"include_usage": True},
    )

    pieces: list[str] = []
    usage: Usage | None = None

    for chunk in stream:
        if getattr(chunk, "usage", None):
            usage = Usage.from_response(chunk.usage)

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        if delta.content:
            pieces.append(delta.content)

    text = "".join(pieces).strip()

    print(f"Response: {text}")
    print(f"Usage: {usage}")

    assert text, "empty completion"
    assert usage is not None, "usage missing"
    assert usage.prompt_tokens > 0, "prompt tokens not reported"


# ================================
# --> Test 2: Agent end-to-end with one tool call
# ================================


@agent_tool(name="get_weather")
def get_weather(city: str) -> str:
    """Get fake weather for a city. Returns a YAML-ish response.

    Args:
        city: City name.
    """
    fakes = {
        "san francisco": {"city": "San Francisco", "temp_f": 63, "condition": "foggy"},
        "miami": {"city": "Miami", "temp_f": 84, "condition": "humid"},
        "denver": {"city": "Denver", "temp_f": 51, "condition": "windy"},
    }

    data = fakes.get(city.lower())

    if data is None:
        return success_response({"city": city, "temp_f": 70, "condition": "unknown"})

    return success_response(data)


def test_agent_end_to_end() -> None:
    """Full Agent.run() — should issue a tool call and produce a final answer."""
    _section("Test 2: Agent.run() with one tool")

    agent = Agent(
        model="anthropic/claude-sonnet-4.6",
        max_iterations=10,
        print_mode=PrintMode.PRODUCTION,
        tools=[get_weather],
    )

    result = agent.run(
        user_message="What's the weather in Miami? Use the tool and report concisely.",
    )

    print(f"\nAnswer: {result.answer}")
    print(f"Iterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Cache write: {result.cache_write_tokens} | Cache read: {result.cached_tokens}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")

    assert result.stop_reason == "answer_ready", f"expected answer_ready, got {result.stop_reason}"
    assert result.tokens_used > 0, "no tokens reported"
    assert "get_weather" in result.tool_calls_made, "tool was not called"
    assert "miami" in result.answer.lower() or "84" in result.answer, "answer did not reference the tool output"


# ================================
# --> Main
# ================================


if __name__ == "__main__":
    _require_env()

    test_raw_streaming_call()
    test_agent_end_to_end()

    print("\nAll smoke tests passed.")
