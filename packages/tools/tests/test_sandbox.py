"""Smoke test — runs an Agent with sandbox tools against a real E2B sandbox.


Opens a sandbox, scaffolds a strategy, inspects files, and closes it.
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_tools.sandbox.lifecycle import start_sandbox, close_sandbox, get_sandbox_status
from prophitai_tools.sandbox.execution import sandbox_bash
from prophitai_tools.sandbox.scaffolding import scaffold_strategy


SANDBOX_TOOLS = [
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_bash, scaffold_strategy,
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


def test_scaffold_and_inspect():
    """Open a sandbox, scaffold a strategy, inspect the files, and close."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "1. Start a sandbox with strategy name 'test_scaffold'.\n"
            "2. Scaffold a new strategy called 'test_scaffold_ma'.\n"
            "3. Test to see if the get_price_data_df function works \n"
            "8. Close the sandbox."
        ),
    )
    _print_result("Scaffold and inspect", result)


if __name__ == "__main__":
    print("Running sandbox smoke tests...\n")
    test_scaffold_and_inspect()
