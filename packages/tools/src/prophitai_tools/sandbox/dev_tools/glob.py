"""Sandbox glob tool for file discovery by pattern."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox


# ================================
# --> Helper funcs
# ================================


DEFAULT_EXCLUDES = [".git", "__pycache__", ".venv", ".ruff_cache", "node_modules"]

MAX_RESULTS = 100


def build_find_command(pattern: str, search_root: str) -> str:
    """Build a find command with excludes and modification-time sorting.

    Uses find to locate files matching the pattern, excludes noisy directories,
    and sorts by modification time (newest first).
    """
    exclude_clauses = " ".join(
        f'-not -path "*/{d}/*"' for d in DEFAULT_EXCLUDES
    )

    return (
        f'cd {search_root} && '
        f'find . -name "{pattern}" -type f {exclude_clauses} '
        f'-printf "%T@ %p\\n" 2>/dev/null | '
        f'sort -rn | cut -d" " -f2- | head -n {MAX_RESULTS + 1}'
    )


def parse_find_output(raw: str, search_root: str) -> dict:
    """Parse find output into structured file list.

    Returns dict with files, total_found, truncated, and search_root.
    """
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]

    truncated = len(lines) > MAX_RESULTS
    files = lines[:MAX_RESULTS]

    # Reason: Replace leading ./ with the absolute search root for clarity
    resolved = [
        f"{search_root}/{f.lstrip('./')}" if f.startswith("./") else f
        for f in files
    ]

    return {
        "files": resolved,
        "total_found": len(resolved),
        "truncated": truncated,
        "search_root": search_root,
    }


# ================================
# --> Tools
# ================================


@agent_tool(name="sandbox_glob", category="sandbox")
def sandbox_glob(sandbox_id: str, pattern: str, path: str = "") -> str:
    """Find files in the sandbox by glob pattern, sorted by modification time (newest first).

    Use this to explore project structure, find specific file types,
    or locate recently changed files. Results exclude .git, __pycache__,
    and .venv directories by default.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        pattern: Glob pattern to match filenames (e.g. "*.py", "*.yaml", "config.*").
        path: Root directory to search from. Defaults to the strategies repo root.
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(
            f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox."
        )

    search_root = path or REPO_PATH

    try:
        # Reason: Verify the search root exists before running find
        check = sandbox.commands.run(f'test -d {search_root} && echo exists || echo missing')

        if "missing" in check.stdout:
            return error_response(f"Directory not found: {search_root}")

        cmd = build_find_command(pattern, search_root)
        result = sandbox.commands.run(cmd, timeout=30)

        if result.exit_code != 0 and result.stderr:
            return error_response(f"Glob search failed: {result.stderr}")

        if not result.stdout.strip():
            return success_response({
                "files": [],
                "total_found": 0,
                "truncated": False,
                "search_root": search_root,
                "message": f"No files matching '{pattern}' found in {search_root}.",
            })

        parsed = parse_find_output(result.stdout, search_root)

        return success_response(parsed)

    except Exception as e:
        return error_response(f"Failed to search files: {e}")
