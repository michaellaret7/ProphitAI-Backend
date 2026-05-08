"""Truncation helpers for tool output displayed via callbacks/streams."""

from typing import Any


MAX_TOOL_RESULT_CHARS = 2000


def truncate_for_display(result: Any) -> str:
    """Stringify a tool result and clip it for display channels (UI, logs)."""
    result_str = str(result)

    if len(result_str) > MAX_TOOL_RESULT_CHARS:
        return result_str[:MAX_TOOL_RESULT_CHARS] + "... (truncated)"

    return result_str
