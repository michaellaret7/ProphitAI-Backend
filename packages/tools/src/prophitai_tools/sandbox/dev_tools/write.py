"""Sandbox file-writing tool with automatic post-write diagnostics.

Writes files into an E2B sandbox using the native filesystem API and
immediately runs ruff check + ruff format to surface lint/formatting
errors so the agent can self-correct in the next iteration.
"""

from e2b.sandbox_sync.commands.command_handle import CommandExitException

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import get_sandbox
from prophitai_tools.sandbox.dev_tools.diagnostics import run_diagnostics


# ================================
# --> Helper funcs
# ================================


def _check_syntax(sandbox, file_path: str) -> str | None:
    """Run a fast ast.parse syntax check on a Python file.

    Args:
        sandbox: Active E2B sandbox instance.
        file_path: Absolute path to the Python file.

    Returns:
        Error message string if syntax is invalid, None if valid.
    """
    cmd = f"python -c \"import ast; ast.parse(open('{file_path}').read())\""

    try:
        sandbox.commands.run(cmd, timeout=10)
        return None

    except CommandExitException as e:
        return e.stderr.strip()


# ================================
# --> Tools
# ================================


@agent_tool(name="sandbox_write", category="sandbox")
def sandbox_write(sandbox_id: str, file_path: str, content: str) -> str:
    """Write or overwrite a file in the sandbox with automatic linting.

    Creates or overwrites a file using the sandbox filesystem API (no shell
    escaping needed), then runs ruff check and ruff format to report any
    lint or formatting issues. For Python files, a fast syntax check via
    ast.parse runs first.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        file_path: Absolute path to write (e.g. '/home/user/strategies/src/my_strategy.py').
        content: Full file content to write.

    Returns:
        Dict with file_path, action (created/overwritten), bytes_written,
        and diagnostics (lint_errors, format_clean). If the file is not
        a Python file, diagnostics will be None.

    Examples:
        sandbox_write(sandbox_id="abc123", file_path="/home/user/strategies/src/main.py", content="print('hello')")
        >>> {"success": True, "data": {"file_path": "...", "action": "created", "bytes_written": 15, "diagnostics": {...}}}
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    try:
        # Reason: test -f returns exit code 1 when the file doesn't exist,
        # which E2B raises as CommandExitException — expected behavior here
        try:
            sandbox.commands.run(f"test -f {file_path}", timeout=5)
            action = "overwritten"

        except CommandExitException:
            action = "created"

        # Reason: Ensure parent directories exist before writing
        parent_dir = "/".join(file_path.rsplit("/", 1)[:-1])

        if parent_dir:
            sandbox.commands.run(f"mkdir -p {parent_dir}", timeout=5)

        # Reason: E2B native file API avoids shell escaping issues with heredocs/echo
        sandbox.files.write(file_path, content)

        bytes_written = len(content.encode("utf-8"))

        # Reason: Only run Python-specific diagnostics on .py files
        diagnostics = None
        is_python = file_path.endswith(".py")

        if is_python:
            syntax_error = _check_syntax(sandbox, file_path)

            if syntax_error:
                return success_response({
                    "file_path": file_path,
                    "action": action,
                    "bytes_written": bytes_written,
                    "syntax_error": syntax_error,
                    "diagnostics": None,
                })

            diagnostics = run_diagnostics(sandbox, file_path)

        return success_response({
            "file_path": file_path,
            "action": action,
            "bytes_written": bytes_written,
            "diagnostics": diagnostics,
        })

    except Exception as e:
        return error_response(f"Failed to write file '{file_path}': {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(sandbox_write.tool)
