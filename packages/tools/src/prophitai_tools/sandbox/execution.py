"""Sandbox execution tool for running shell commands."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox

BLOCKED_REPOS = [
    "https://github.com/Prophit-AI/ProphitAI.git",
    "https://github.com/Prophit-AI/webapp.git",
]


@agent_tool(name="sandbox_bash", category="sandbox")
def sandbox_bash(sandbox_id: str, command: str, timeout: int = 1200) -> str:
    """Run a shell command inside the sandbox.

    This is the single execution tool for all sandbox operations: file I/O,
    Python scripts, git commands, linting, testing, and any other CLI work.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        command: Shell command to execute (e.g. "cat main.py", "python strategy.py", "ls -la").
        timeout: Max seconds to wait for the command to finish.
    """
    # Reason: prevent cloning proprietary repos into the sandbox
    if "git clone" in command or "git pull" in command:
        cmd_lower = command.lower()
        for repo in BLOCKED_REPOS:
            if repo.lower() in cmd_lower or repo.replace(".git", "").lower() in cmd_lower:
                return error_response(f"Cloning or pulling from '{repo}' is not permitted in the sandbox.")

    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    try:
        # Reason: Auto-activate the project venv so `python` resolves correctly
        wrapped = f"source {REPO_PATH}/.venv/bin/activate && {command}"
        result = sandbox.commands.run(wrapped, timeout=timeout)
        return success_response({
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })

    except Exception as e:
        return error_response(f"Failed to run command: {e}")
