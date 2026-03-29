"""Sandbox lifecycle tools for starting, closing, and checking sandbox status."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import (
    REPO_PATH,
    STRATEGIES_REPO,
    create_sandbox,
    get_sandbox,
    remove_sandbox,
)


# ================================
# --> Helper funcs
# ================================


def bootstrap_repo(sandbox, strategy_name: str) -> dict[str, str]:
    """Clone the strategies repo and create/checkout the strategy branch.

    Returns:
        Dict with branch name and repo path for the response.
    """
    branch = f"strategy/{strategy_name}"

    # Reason: Use GITHUB_TOKEN (injected via SANDBOX_ prefix stripping) for private repo auth
    clone_cmd = (
        f'if [ -n "$GITHUB_TOKEN" ]; then '
        f'  git clone https://$GITHUB_TOKEN@github.com/Prophit-AI/Strategies.git {REPO_PATH}; '
        f"else "
        f"  git clone {STRATEGIES_REPO} {REPO_PATH}; "
        f"fi"
    )
    sandbox.commands.run(clone_cmd)

    # Reason: Check if remote branch exists first; if so, check it out instead of creating new
    checkout_cmd = (
        f"cd {REPO_PATH} && "
        f"git fetch origin {branch} 2>/dev/null && "
        f"git checkout {branch} 2>/dev/null || "
        f"git checkout -b {branch}"
    )
    sandbox.commands.run(checkout_cmd)

    # Reason: Configure git identity for commits inside the sandbox
    sandbox.commands.run(
        f'cd {REPO_PATH} && git config user.email "agent@prophitai.com" && '
        f'git config user.name "ProphitAI Agent"'
    )

    # Reason: Write ~/.netrc so all git HTTPS calls (including uv's internal git fetch)
    # authenticate against github.com with the token.
    sandbox.commands.run(
        'if [ -n "$GITHUB_TOKEN" ]; then '
        'printf "machine github.com\\nlogin x-access-token\\npassword %s\\n" "$GITHUB_TOKEN" '
        '> ~/.netrc && chmod 600 ~/.netrc; '
        'fi'
    )

    # Reason: Install dependencies so strategy imports work
    sandbox.commands.run(f"cd {REPO_PATH} && uv sync", timeout=300)

    return {"branch": branch, "repo_path": REPO_PATH}


# ================================
# --> Tools
# ================================


@agent_tool(name="start_sandbox", category="sandbox")
def start_sandbox(strategy_name: str, timeout_minutes: int = 60) -> str:
    """Start a new sandbox environment for strategy development.

    Creates an isolated E2B microVM, clones the strategies repo,
    checks out or creates a strategy branch, and installs dependencies.
    The sandbox persists across tool calls until closed or timed out.

    Args:
        strategy_name: Name of the strategy (used for branch name: strategy/{name}).
        timeout_minutes: How long the sandbox stays alive in minutes.
    """
    try:
        timeout_seconds = timeout_minutes * 60
        sandbox_id, sandbox = create_sandbox(timeout=timeout_seconds)
        repo_info = bootstrap_repo(sandbox, strategy_name)
        return success_response({
            "sandbox_id": sandbox_id,
            "branch": repo_info["branch"],
            "repo_path": repo_info["repo_path"],
            "timeout_minutes": timeout_minutes,
            "status": "running",
        })
    except Exception as e:
        return error_response(f"Failed to start sandbox: {e}")


@agent_tool(name="close_sandbox", category="sandbox")
def close_sandbox(sandbox_id: str) -> str:
    """Close a running sandbox and release its resources.

    Any uncommitted or unpushed work will be lost.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'.")
    try:
        sandbox.kill()
        remove_sandbox(sandbox_id)
        return success_response({"sandbox_id": sandbox_id, "status": "closed"})
    except Exception as e:
        remove_sandbox(sandbox_id)
        return error_response(f"Error closing sandbox: {e}")


@agent_tool(name="get_sandbox_status", category="sandbox")
def get_sandbox_status(sandbox_id: str) -> str:
    """Check if a sandbox is still running.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        return error_response(
            f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox."
        )
    try:
        running = sandbox.is_running()
        return success_response({
            "sandbox_id": sandbox_id,
            "is_running": running,
            "status": "running" if running else "stopped",
        })
    except Exception as e:
        return error_response(f"Failed to check sandbox status: {e}")
