"""Scaffold tool for copying the strategy template into a new development folder."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox

TEMPLATE_PATH = f"{REPO_PATH}/strategies/template"
DEVELOPMENT_PATH = f"{REPO_PATH}/strategies/development"


@agent_tool(name="scaffold_strategy", category="sandbox")
def scaffold_strategy(sandbox_id: str, strategy_name: str) -> str:
    """Copy the strategy template into a new development folder.

    Creates strategies/development/{strategy_name}/ from the canonical
    template scaffold. Use this before writing any strategy code to ensure
    a consistent starting structure.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        strategy_name: Name for the new strategy folder (e.g. rsi_mean_reversion).
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    target_path = f"{DEVELOPMENT_PATH}/{strategy_name}"

    try:
        # Reason: Check if folder already exists to avoid silent overwrites
        check = sandbox.commands.run(f"test -d {target_path} && echo exists || echo missing")
        if "exists" in check.stdout:
            return error_response(f"Strategy folder already exists at {target_path}.")

        sandbox.commands.run(f"mkdir -p {DEVELOPMENT_PATH}")
        result = sandbox.commands.run(f"cp -r {TEMPLATE_PATH} {target_path}")

        if result.exit_code != 0:
            return error_response(f"Copy failed: {result.stderr}")

        return success_response({
            "strategy_name": strategy_name,
            "path": target_path,
            "status": "scaffolded",
        })

    except Exception as e:
        return error_response(f"Failed to scaffold strategy: {e}")
