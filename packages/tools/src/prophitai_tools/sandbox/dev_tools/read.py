"""Sandbox file-reading tool with line numbers and range support."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import REPO_PATH, get_sandbox

MAX_OUTPUT_BYTES = 50_000


# ================================
# --> Helper funcs
# ================================

def _run(sandbox, command: str, timeout: int = 30):
    """Run a command inside the sandbox with venv activation."""
    wrapped = f"source {REPO_PATH}/.venv/bin/activate && {command}"

    return sandbox.commands.run(wrapped, timeout=timeout)


def _format_lines(raw: str, offset: int) -> str:
    """Add compact line numbers to raw file content.

    Produces `{line_no}  {content}` with line numbers starting at offset + 1.
    Empty source lines get just the line number (no trailing whitespace) so
    that PyYAML can use block-scalar style instead of falling back to quoted.
    """
    lines = raw.splitlines()
    numbered = [
        f"{offset + i + 1}  {line}" if line else str(offset + i + 1)
        for i, line in enumerate(lines)
    ]

    return "\n".join(numbered)


def _nearest_existing_ancestor(sandbox, file_path: str) -> tuple[str, str] | None:
    """Walk up from a missing path until an existing directory is found.

    Returns (ancestor_path, listing) or None if nothing along the chain exists.
    Caps the walk at 8 levels to bound shell calls when an agent passes a path
    rooted in a totally wrong place.
    """
    current = file_path.rstrip("/")

    for _ in range(8):
        # Reason: strip last segment to step up one level
        if "/" not in current or current == "/":
            return None

        current = current.rsplit("/", 1)[0] or "/"

        check = _run(sandbox, f"test -d {current} && echo DIR || echo NO")

        if check.stdout.strip() == "DIR":
            listing = _run(sandbox, f"ls -1 {current}")

            return current, listing.stdout

    return None


# ================================
# --> Tools
# ================================

@agent_tool(name="sandbox_read", category="sandbox")
def sandbox_read(
    sandbox_id: str,
    file_path: str,
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """Read a file from the sandbox with line numbers.

    Returns formatted, line-numbered output for a file inside the sandbox.
    If the path is a directory, returns its listing instead. Detects binary
    files and rejects them to avoid dumping garbage into context.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        file_path: Absolute path in the sandbox (e.g. /home/user/strategies/development/my_strat/strategy.py).
        offset: Start reading from this line number (0-indexed, default 0).
        limit: Maximum number of lines to return (default 2000).

    Returns:
        YAML-formatted result with file_path, total_lines, lines_shown, and content.

    Examples:
        sandbox_read(sandbox_id="abc123", file_path="/home/user/strategies/development/my_strat/strategy.py")
        sandbox_read(sandbox_id="abc123", file_path="/home/user/strategies/development/my_strat/strategy.py", offset=50, limit=100)
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    try:
        # Reason: If path is a directory, return a listing instead of erroring
        dir_check = _run(sandbox, f"test -d {file_path} && echo DIR || echo NOT_DIR")

        if dir_check.stdout.strip() == "DIR":
            listing = _run(sandbox, f"ls -la {file_path}")

            return success_response({
                "file_path": file_path,
                "type": "directory",
                "content": listing.stdout,
            })

        # Reason: Verify the file exists before attempting to read
        file_check = _run(sandbox, f"test -f {file_path} && echo EXISTS || echo MISSING")

        if file_check.stdout.strip() != "EXISTS":
            # Reason: On miss, surface the nearest existing ancestor's listing so
            # the agent can correct the path in one step instead of probing blindly.
            hint = _nearest_existing_ancestor(sandbox, file_path)

            if hint is None:
                return error_response(f"File not found: {file_path} (no ancestor directory exists — check sandbox_id and absolute-path prefix).")

            ancestor, listing = hint
            truncated = listing if len(listing) <= 2_000 else listing[:2_000] + "\n... (truncated)"

            return error_response(
                f"File not found: {file_path}\n"
                f"Nearest existing directory: {ancestor}\n"
                f"Contents:\n{truncated}"
            )

        # Reason: Detect binary files to prevent dumping non-printable bytes into context
        mime_check = _run(sandbox, f"file --mime-encoding {file_path}")

        if "binary" in mime_check.stdout.lower():
            return error_response(f"Binary file detected, cannot read: {file_path}")

        # Reason: Get total line count so the agent knows how much of the file it's seeing
        wc_result = _run(sandbox, f"wc -l < {file_path}")
        total_lines = int(wc_result.stdout.strip())

        # Reason: Read raw lines with sed for offset/limit, then format ourselves
        # to avoid cat -n's wasteful 6-char padding
        start_line = offset + 1
        end_line = offset + limit
        read_cmd = f"sed -n '{start_line},{end_line}p' {file_path}"
        read_result = _run(sandbox, read_cmd)

        raw = read_result.stdout
        content = _format_lines(raw, offset)
        lines_shown = len(raw.splitlines())

        # Reason: Cap output at 50KB to prevent blowing the agent's context window
        if len(content.encode("utf-8")) > MAX_OUTPUT_BYTES:
            content = content.encode("utf-8")[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
            content += "\n\n--- OUTPUT TRUNCATED (exceeded 50KB limit) ---"

        return success_response({
            "file_path": file_path,
            "total_lines": total_lines,
            "lines_shown": lines_shown,
            "offset": offset,
            "content": content,
        })

    except Exception as e:
        return error_response(f"Failed to read file: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print("sandbox_read requires an active E2B sandbox. Run via test_sandbox_read.py.")
