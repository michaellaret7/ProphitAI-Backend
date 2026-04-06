"""Smoke test — runs an Agent with sandbox tools against a real E2B sandbox.


Opens a sandbox, reads files, runs bash commands, and closes it.
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_tools.sandbox.lifecycle import start_sandbox, close_sandbox, get_sandbox_status
from prophitai_tools.sandbox.execution import sandbox_bash


SANDBOX_TOOLS = [
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_bash,
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


def test_sandbox_full_flow():
    """Open a sandbox, read files, run bash, and close."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            """
            start a sandbox with strategy name 'test_flow'
            check all of the local and remote branches and return them
            """
        ),
    )
    _print_result("Sandbox full flow", result)


if __name__ == "__main__":
    print("Running sandbox smoke tests...\n")
    test_sandbox_full_flow()
