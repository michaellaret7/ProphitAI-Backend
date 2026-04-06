"""Test that an agent can use the append_memory tool to write to memory.md.

Creates a bare Agent with only append_memory registered, gives it a task
that forces a tool call, and verifies the memory file has content afterward.
"""

from functools import partial
from pathlib import Path

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_fund.tools import append_memory


MEMORY_FILE = Path(__file__).parent / "memory.md"

SYSTEM_PROMPT = (
    "You are a test agent. You have one job: use the append_memory tool "
    "to write a memory entry, then respond with 'done'."
    "Build a structured memory entry"
)


def run_test() -> None:
    """Instantiate an agent with append_memory, ask it to write, and verify the file."""

    # Reason: start clean so we can verify the tool actually wrote something
    if MEMORY_FILE.exists():
        MEMORY_FILE.unlink()

    agent = Agent(
        system_prompt=SYSTEM_PROMPT,
        print_mode=PrintMode.VERBOSE,
    )

    tool = {k: v for k, v in append_memory.tool.items() if k != "function"}
    agent.add_tool(**tool, function=partial(append_memory, MEMORY_FILE))

    response = agent.run(
        "Write a memory entry that says: 'Momentum strategies underperform in choppy, range-bound regimes.'"
    )

    print("\n--- Agent Response ---")
    print(response.answer)

    # --- Verify ---
    assert MEMORY_FILE.exists(), "memory.md was not created"

    content = MEMORY_FILE.read_text(encoding="utf-8").strip()
    assert len(content) > 0, "memory.md is empty"

    print("\n--- Memory File Contents ---")
    print(content)
    print("\nTest passed.")


if __name__ == "__main__":
    run_test()
