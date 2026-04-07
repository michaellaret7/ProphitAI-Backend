"""Sandbox grep tool for code search with ripgrep/grep fallback."""

from e2b.sandbox_sync.commands.command_handle import CommandExitException

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox

MAX_MATCHES = 100
MAX_LINE_LENGTH = 500
DEFAULT_EXCLUDES = [".git", "__pycache__", ".venv", ".ruff_cache", "node_modules"]


# ================================
# --> Helper funcs
# ================================


def _build_grep_command(pattern: str, search_root: str, include: str) -> str:
    """Build a grep command, preferring ripgrep with grep -rn fallback.

    Uses `rg` if available, otherwise falls back to `grep -rn` which is
    universally available. Both produce the same path:line:text format.

    Args:
        pattern: Regex pattern to search for.
        search_root: Directory or file to search in.
        include: Glob filter for file types (e.g. "*.py").

    Returns:
        Complete shell command string.
    """
    # Reason: Try ripgrep first for speed, fall back to grep -rn
    rg_parts = [
        "rg",
        "--line-number",
        "--no-heading",
        f"--max-count={MAX_MATCHES}",
        "--color=never",
    ]

    for exclude in DEFAULT_EXCLUDES:
        rg_parts.append(f"--glob '!{exclude}'")

    if include:
        rg_parts.append(f"--glob '{include}'")

    rg_parts.append(f"'{pattern}'")
    rg_parts.append(search_root)
    rg_cmd = " ".join(rg_parts)

    # Reason: grep -rn fallback with --include and --exclude-dir filtering
    grep_parts = [
        "grep -rn",
        "--color=never",
    ]

    for exclude in DEFAULT_EXCLUDES:
        grep_parts.append(f"--exclude-dir='{exclude}'")

    if include:
        grep_parts.append(f"--include='{include}'")

    grep_parts.append(f"'{pattern}'")
    grep_parts.append(search_root)

    # Reason: Pipe through head to cap results, matching ripgrep's --max-count
    grep_cmd = " ".join(grep_parts) + f" | head -n {MAX_MATCHES + 1}"

    return f"command -v rg > /dev/null 2>&1 && {rg_cmd} || {grep_cmd}"


def _parse_rg_output(raw: str) -> dict:
    """Parse ripgrep output into structured grouped-by-file results.

    Input format from rg --no-heading --line-number:
        path/file.py:10:matched line text

    Returns:
        Dict with matches (grouped by file), total_matches, and truncated flag.
    """
    if not raw.strip():
        return {"matches": {}, "total_matches": 0, "truncated": False}

    matches: dict[str, list[dict]] = {}
    total = 0

    for line in raw.strip().splitlines():
        # Reason: ripgrep output is path:line_no:text — split on first two colons
        parts = line.split(":", 2)

        if len(parts) < 3:
            continue

        file_path = parts[0]
        line_no = parts[1]
        text = parts[2]

        # Reason: Truncate long lines to prevent context overflow
        if len(text) > MAX_LINE_LENGTH:
            text = text[:MAX_LINE_LENGTH] + " ..."

        if file_path not in matches:
            matches[file_path] = []

        matches[file_path].append({"line": int(line_no), "text": text})
        total += 1

    truncated = total >= MAX_MATCHES

    return {
        "matches": matches,
        "total_matches": total,
        "truncated": truncated,
    }


# ================================
# --> Tools
# ================================


@agent_tool(name="sandbox_grep", category="sandbox")
def sandbox_grep(
    sandbox_id: str,
    pattern: str,
    path: str = "",
    include: str = "",
) -> str:
    """Search file contents in the sandbox using ripgrep.

    Finds lines matching a regex pattern across the codebase, grouped by file
    with line numbers. Use this to find function definitions, imports, usages,
    and patterns across the strategies repo.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        pattern: Regex pattern to search for (ripgrep syntax, e.g. "def calculate", "import pandas").
        path: Directory or file to search in. Defaults to the strategies repo root.
        include: Glob filter for file types (e.g. "*.py", "*.yaml"). Empty means all files.

    Returns:
        Dict with matches grouped by file path, total_matches count, and truncated flag.

    Examples:
        sandbox_grep(sandbox_id="abc123", pattern="def run_strategy")
        sandbox_grep(sandbox_id="abc123", pattern="import numpy", include="*.py")
        sandbox_grep(sandbox_id="abc123", pattern="API_KEY", path="/home/user/strategies/strategies/development")
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    search_root = path or REPO_PATH

    no_matches_response = success_response({
        "matches": {},
        "total_matches": 0,
        "truncated": False,
        "message": f"No matches for '{pattern}' in {search_root}.",
    })

    try:
        cmd = _build_grep_command(pattern, search_root, include)
        result = sandbox.commands.run(cmd, timeout=30)

        if not result.stdout.strip():
            return no_matches_response

        parsed = _parse_rg_output(result.stdout)

        return success_response(parsed)

    except CommandExitException as e:
        # Reason: Both rg and grep exit with code 1 when no matches are found
        if e.exit_code == 1:
            return no_matches_response

        return error_response(f"Failed to search: {e.stderr or e.stdout}")

    except Exception as e:
        return error_response(f"Failed to search: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(sandbox_grep.tool)
