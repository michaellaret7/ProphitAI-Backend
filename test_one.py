from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "packages" / "atlas" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode


PROMPT = (
    "Research Microsoft. Use web search to gather current information, then give me a concise summary "
    "covering: what Microsoft does, the most important recent developments, and one key risk to watch. "
    "Keep the final answer short and practical."
)


def safe_print(text: object = "") -> None:
    rendered = str(text)
    try:
        print(rendered)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(rendered.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def main() -> None:
    agent = Agent(
        provider="openai",
        model="gpt-5.4",
        print_mode=PrintMode.PRODUCTION,
        temperature=0.7,
    )

    safe_print("=" * 80)
    safe_print("Atlas Microsoft Test")
    safe_print("=" * 80)
    safe_print(f"Provider: {agent.provider}")
    safe_print(f"Model: {agent.model}")
    safe_print(f"Registered tools: {sorted(agent.get_tool_names())}")
    safe_print("-" * 80)
    safe_print("Prompt:")
    safe_print(PROMPT)
    safe_print("-" * 80)

    response = agent.run(PROMPT)

    safe_print("\nFinal Answer:\n")
    safe_print(response.answer)
    safe_print("\nRun Stats:")
    safe_print(f"  Tool calls made: {response.tool_calls_made}")
    safe_print(f"  Iterations: {response.iterations}")
    safe_print(f"  Tokens used: {response.tokens_used}")
    safe_print(f"  Cache creation input tokens: {response.cache_creation_input_tokens}")
    safe_print(f"  Cache read input tokens: {response.cache_read_input_tokens}")
    safe_print(f"  Stop reason: {response.stop_reason}")


if __name__ == "__main__":
    main()
