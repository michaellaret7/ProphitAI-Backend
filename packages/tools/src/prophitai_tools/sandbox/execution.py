"""Sandbox execution tools for running Python code and shell commands."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import get_sandbox

BLOCKED_REPOS = [
    "https://github.com/Prophit-AI/ProphitAI.git",
    "https://github.com/Prophit-AI/webapp.git",
]


@agent_tool(name="sandbox_run_python", category="sandbox")
def sandbox_run_python(sandbox_id: str, code: str) -> str:
    """Execute Python code inside the sandbox.

    The code runs in the sandbox's Python environment with all prophitai
    packages available. Use this for quick computations, data exploration,
    or running strategy logic directly.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        code: Python code to execute.
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    try:
        execution = sandbox.run_code(code)
        stdout = "\n".join(execution.logs.stdout) if execution.logs.stdout else ""
        stderr = "\n".join(execution.logs.stderr) if execution.logs.stderr else ""
        results = [str(r) for r in execution.results] if execution.results else []
        response = {
            "stdout": stdout,
            "stderr": stderr,
            "results": results,
        }
        
        if execution.error:
            response["error"] = str(execution.error)

        return success_response(response)

    except Exception as e:
        return error_response(f"Failed to execute Python code: {e}")


@agent_tool(name="sandbox_run_command", category="sandbox")
def sandbox_run_command(sandbox_id: str, command: str, timeout: int = 1200) -> str:
    """Run a shell command inside the sandbox.

    Use this for git operations, pip installs, linting, running test scripts,
    or any other CLI command.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        command: Shell command to execute (e.g. "cd /home/user/strategies && python main.py").
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
        result = sandbox.commands.run(command, timeout=timeout)
        return success_response({
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        })

    except Exception as e:
        return error_response(f"Failed to run command: {e}")
