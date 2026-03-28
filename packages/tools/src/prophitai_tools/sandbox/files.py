"""Sandbox file tools for reading, writing, and listing files in the sandbox."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox


@agent_tool(name="sandbox_write_file", category="sandbox")
def sandbox_write_file(sandbox_id: str, path: str, content: str) -> str:
    """Write a file to the sandbox filesystem.

    Use this to create or overwrite strategy files, test scripts, or config files
    inside the sandbox.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        path: Absolute path on the sandbox (e.g. /home/user/strategies/strategies/my_strat/strategy.py).
        content: The file content to write.
    """
    sandbox = get_sandbox(sandbox_id)
    
    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")
    try:
        sandbox.files.write(path, content)
        return success_response({"path": path, "bytes_written": len(content.encode())})
    except Exception as e:
        return error_response(f"Failed to write file: {e}")


@agent_tool(name="sandbox_read_file", category="sandbox")
def sandbox_read_file(sandbox_id: str, path: str) -> str:
    """Read a file from the sandbox filesystem.

    Use this to inspect strategy code, backtest results, or log files.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        path: Absolute path on the sandbox to read.
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")
    try:
        content = sandbox.files.read(path)
        return success_response({"path": path, "content": content})
    except Exception as e:
        return error_response(f"Failed to read file: {e}")


@agent_tool(name="sandbox_list_files", category="sandbox")
def sandbox_list_files(sandbox_id: str, path: str = "/home/user/strategies") -> str:
    """List files and directories at a path in the sandbox.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        path: Directory path to list. Defaults to the strategies repo root.
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")
    try:
        entries = sandbox.files.list(path)
        files = [entry.name for entry in entries]
        return success_response({"path": path, "files": files})
    except Exception as e:
        return error_response(f"Failed to list files: {e}")


@agent_tool(name="sandbox_file_tree", category="sandbox")
def sandbox_file_tree(sandbox_id: str, path: str = REPO_PATH, max_depth: int = 4) -> str:
    """Show the file and folder structure of a directory in ASCII tree format.

    Use this to understand the project layout before writing or modifying files.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        path: Root directory to display. Defaults to the strategies repo.
        max_depth: How many levels deep to show.
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")
    try:
        # Reason: Use find + sed to build an ASCII tree; avoids needing `tree` installed
        cmd = (
            f"find {path} -maxdepth {max_depth} "
            f"-not -path '*/.git/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*' "
            f"| sort "
            f"| sed -e 's|{path}||' -e 's|[^/]*/|  |g' -e 's|  \\([^ ]\\)|── \\1|'"
        )
        result = sandbox.commands.run(cmd)
        return success_response({"path": path, "tree": result.stdout})
    except Exception as e:
        return error_response(f"Failed to get file tree: {e}")
