"""Smoke test — runs an Agent with sandbox tools to test sandbox_glob.

Opens a sandbox, scaffolds a strategy, uses sandbox_glob to discover
files by pattern, and closes the sandbox.
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_tools.sandbox.lifecycle import start_sandbox, close_sandbox, get_sandbox_status
from prophitai_tools.sandbox.execution import sandbox_bash
from prophitai_tools.sandbox.scaffolding import scaffold_strategy
from prophitai_tools.sandbox.dev_tools.glob import sandbox_glob


SANDBOX_TOOLS = [
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_bash, scaffold_strategy, sandbox_glob,
]


# ================================
# --> Helper funcs
# ================================


def _print_result(title: str, result) -> None:
    """Pretty-print an AgentResponse."""
    print("\n" + "=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)
    print(f"Answer:\n{result.answer}")
    print(f"\nIterations: {result.iterations}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Tool calls: {result.tool_calls_made}")
    print(f"Stop reason: {result.stop_reason}")


def _make_agent() -> Agent:
    """Create an Agent loaded with sandbox tools."""
    return Agent(
        provider="anthropic",
        model="claude-sonnet-4-6",
        print_mode=PrintMode.DEBUG,
        tools=SANDBOX_TOOLS,
    )


# ================================
# --> Tests
# ================================


def test_sandbox_glob():
    """Open a sandbox, scaffold a strategy, glob for files, and close."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "1. Start a sandbox with strategy name 'test_glob'.\n"
            "2. Scaffold a new strategy called 'test_glob_strat'.\n"
            "3. Use sandbox_glob to find all '*.py' files in the repo.\n"
            "4. Use sandbox_glob to find all '*.yaml' files.\n"
            "5. Use sandbox_glob with a pattern that should return no results (e.g. '*.xyz').\n"
            "6. Report what files were found for each glob call.\n"
            "7. Close the sandbox."
        ),
    )
    _print_result("sandbox_glob", result)


if __name__ == "__main__":
    print("Running sandbox_glob smoke test...\n")
    test_sandbox_glob()
