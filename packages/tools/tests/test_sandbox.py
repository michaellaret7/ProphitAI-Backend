"""Smoke test — runs an Agent with sandbox tools against a real E2B sandbox.


Opens a sandbox, views the file tree, and closes it.
"""

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode

from prophitai_tools.sandbox.lifecycle import start_sandbox, close_sandbox, get_sandbox_status
from prophitai_tools.sandbox.files import sandbox_write_file, sandbox_read_file, sandbox_list_files, sandbox_file_tree
from prophitai_tools.sandbox.execution import sandbox_run_python, sandbox_run_command


SANDBOX_TOOLS = [
    start_sandbox, close_sandbox, get_sandbox_status,
    sandbox_write_file, sandbox_read_file, sandbox_list_files, sandbox_file_tree,
    sandbox_run_python, sandbox_run_command,
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
        print_mode=PrintMode.PRODUCTION,
        tools=SANDBOX_TOOLS,
    )


# ================================
# --> Tests
# ================================


def test_sandbox_file_tree():
    """Open a sandbox, view the file tree, and close it."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "1. Start a sandbox with strategy name 'test_smoke'.\n"
            "2. Use the file tree tool to see the project structure.\n"
            "3. Report what you see.\n"
            "4. Close the sandbox."
        ),
        max_iterations=10,
    )
    _print_result("Sandbox file tree", result)


def test_sandbox_readme_commit():
    """Open a sandbox, write a README, commit, push, and close."""
    agent = _make_agent()
    result = agent.run(
        user_message=(
            "1. Start a sandbox with strategy name 'test_readme'.\n"
            "2. Use the file tree tool to see the project structure.\n"
            "3. Write a README.md at the root of the repo. It should say:\n"
            "   '# ProphitAI Strategies\n\n"
            "   Agent-built algorithmic trading strategies for the ProphitAI platform.'\n"
            "4. Commit the README with message 'add README'.\n"
            "5. Push the branch to origin.\n"
            "6. Report what happened.\n"
            "7. Close the sandbox."
        ),
        max_iterations=15,
    )
    _print_result("Sandbox README commit", result)


if __name__ == "__main__":
    print("Running sandbox smoke tests...\n")
    test_sandbox_readme_commit()
