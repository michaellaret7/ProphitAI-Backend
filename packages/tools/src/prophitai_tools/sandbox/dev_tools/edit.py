"""Sandbox file-editing tool with progressive fuzzy matching.

Performs targeted string replacement in sandbox files. When the LLM's
old_string doesn't match verbatim (whitespace / indentation drift),
progressively looser matching strategies are tried before failing.
"""

import difflib
import re

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_tools.sandbox.client import get_sandbox
from prophitai_tools.sandbox.dev_tools.diagnostics import run_diagnostics


# ================================
# --> Helper funcs
# ================================


def _normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to a single space."""
    return re.sub(r"\s+", " ", text).strip()


def _strip_leading_indent(text: str) -> str:
    """Remove leading whitespace from every line."""
    return "\n".join(line.lstrip() for line in text.splitlines())


def _strip_boundary_blanks(text: str) -> str:
    """Strip leading and trailing blank lines (not internal ones)."""
    lines = text.splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines)


def _find_match(content: str, old_string: str) -> tuple[str | None, int, str]:
    """Try progressive matching strategies against file content.

    Returns:
        Tuple of (strategy_name, match_count, matched_text).
        strategy_name is None if no strategy matched.
        matched_text is the verbatim text in content that should be replaced.
    """
    # Reason: Try exact match first — cheapest and most reliable
    count = content.count(old_string)

    if count > 0:
        return ("exact", count, old_string)

    # Reason: Line-based strategies slide a window of N lines over the file
    # and compare after normalization. Window size varies because blank
    # lines may be present in content but absent in old_string.
    line_strategies = [
        ("indent_flexible", _strip_leading_indent),
        ("trimmed_boundary", _strip_boundary_blanks),
    ]

    # Reason: Whitespace normalization flattens everything (including newlines)
    # to a single string, so it needs a variable-width window approach
    normalized_old_ws = _normalize_whitespace(old_string)
    old_line_count = len(old_string.splitlines())
    content_lines = content.splitlines()

    # Reason: Try windows of increasing size to handle cases where the LLM
    # omitted blank lines that exist in the file
    for window_size in range(old_line_count, old_line_count + 3):
        if window_size > len(content_lines):
            break

        matches: list[str] = []

        for i in range(len(content_lines) - window_size + 1):
            window_text = "\n".join(content_lines[i : i + window_size])

            if _normalize_whitespace(window_text) == normalized_old_ws:
                matches.append(window_text)

        if matches:
            return ("whitespace_normalized", len(matches), matches[0])

    for name, normalizer in line_strategies:
        normalized_old = normalizer(old_string)
        old_lines = normalized_old.splitlines()
        matches = []

        for i in range(len(content_lines) - len(old_lines) + 1):
            window = content_lines[i : i + len(old_lines)]
            normalized_window = normalizer("\n".join(window))

            if normalized_window == normalized_old:
                matches.append("\n".join(window))

        if matches:
            return (name, len(matches), matches[0])

    return (None, 0, "")


def _make_diff(old_content: str, new_content: str, file_path: str) -> str:
    """Generate a unified diff snippet between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "".join(diff)


# ================================
# --> Tools
# ================================


@agent_tool(name="sandbox_edit", category="sandbox")
def sandbox_edit(
    sandbox_id: str,
    file_path: str,
    old_string: str,
    new_string: str,
) -> str:
    """Edit a file in the sandbox by replacing old_string with new_string.

    Performs a targeted find-and-replace with progressive fuzzy matching.
    If the exact old_string isn't found, tries whitespace-normalized,
    indent-flexible, and boundary-trimmed matching before failing.
    Requires exactly one match to prevent silent multi-replace corruption.

    After a successful edit, runs ruff check and ruff format on Python
    files to surface any lint or formatting issues.

    Args:
        sandbox_id: The sandbox ID returned by start_sandbox.
        file_path: Absolute path to the file to edit.
        old_string: The text to find and replace. Must match exactly once.
        new_string: The replacement text.

    Returns:
        Dict with file_path, match_strategy, diff preview, and diagnostics.

    Examples:
        sandbox_edit(sandbox_id="abc123", file_path="/home/user/strategies/src/main.py", old_string="def old():", new_string="def new():")
    """
    sandbox = get_sandbox(sandbox_id)

    if not sandbox:
        return error_response(f"No active sandbox with id '{sandbox_id}'. Start one with start_sandbox.")

    if old_string == new_string:
        return error_response("old_string and new_string are identical. No edit needed.")

    try:
        # Reason: Read file content via native API to avoid shell escaping issues
        content = sandbox.files.read(file_path)

        if isinstance(content, bytes):
            content = content.decode("utf-8")

    except Exception as e:
        return error_response(f"Cannot read file '{file_path}': {e}")

    try:
        strategy, count, matched_text = _find_match(content, old_string)

        if strategy is None:
            return error_response(
                f"old_string not found in '{file_path}'. "
                "Read the file first with sandbox_read to get the exact text."
            )

        if count > 1:
            return error_response(
                f"old_string matched {count} times in '{file_path}' (via {strategy} matching). "
                "Provide more surrounding context to make the match unique."
            )

        # Reason: Replace the verbatim matched text (not the normalized version)
        # so indentation and whitespace are preserved correctly
        new_content = content.replace(matched_text, new_string, 1)

        # Reason: Write back via native API to avoid shell escaping
        sandbox.files.write(file_path, new_content)

        diff = _make_diff(content, new_content, file_path)

        # Reason: Only run Python-specific diagnostics on .py files
        diagnostics = None

        if file_path.endswith(".py"):
            diagnostics = run_diagnostics(sandbox, file_path)

        return success_response({
            "file_path": file_path,
            "match_strategy": strategy,
            "diff": diff,
            "diagnostics": diagnostics,
        })

    except Exception as e:
        return error_response(f"Failed to edit file '{file_path}': {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(sandbox_edit.tool)
