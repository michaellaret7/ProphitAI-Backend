"""Shared post-write diagnostics for sandbox dev tools.

Runs ruff check and ruff format --check after file writes so the agent
sees lint / formatting errors immediately and can self-correct.
"""

from e2b_code_interpreter import Sandbox
from e2b.sandbox_sync.commands.command_handle import CommandExitException

from prophitai_tools.sandbox.client import REPO_PATH

# Reason: Cap lint output so a badly broken file doesn't flood the context window
MAX_LINT_ERRORS = 20


# ================================
# --> Helper funcs
# ================================


def _parse_lint_output(stdout: str) -> list[str]:
    """Extract individual lint error lines from ruff check output.

    Args:
        stdout: Raw stdout from ``ruff check``.

    Returns:
        List of error strings, capped at MAX_LINT_ERRORS.
    """
    if not stdout.strip():
        return []

    lines = [
        line.strip()
        for line in stdout.strip().splitlines()
        if line.strip()
        and not line.startswith("Found")
        and not line.startswith("[*]")
    ]

    return lines[:MAX_LINT_ERRORS]


def run_diagnostics(sandbox: Sandbox, file_path: str) -> dict:
    """Run ruff check + ruff format --check on a file inside the sandbox.

    Args:
        sandbox: Active E2B sandbox instance.
        file_path: Absolute path to the file to diagnose.

    Returns:
        Dict with ``lint_errors`` (list[str]) and ``format_clean`` (bool).
    """
    activate = f"source {REPO_PATH}/.venv/bin/activate"

    # Reason: ruff check returns exit code 1 when lint errors are found —
    # CommandExitException carries stdout/stderr with the error details
    lint_cmd = f"{activate} && ruff check {file_path} --output-format=concise"

    try:
        sandbox.commands.run(lint_cmd, timeout=30)
        lint_errors: list[str] = []

    except CommandExitException as e:
        lint_errors = _parse_lint_output(e.stdout)

    # Reason: ruff format --check returns exit code 1 if formatting would change
    format_cmd = f"{activate} && ruff format --check {file_path}"

    try:
        sandbox.commands.run(format_cmd, timeout=30)
        format_clean = True

    except CommandExitException:
        format_clean = False

    return {
        "lint_errors": lint_errors,
        "format_clean": format_clean,
    }
