"""Append-only memory tool for fund agents.

Writes structured memory entries to a per-agent memory.md file. The file path
is pre-bound via functools.partial at agent init time — the LLM sees only
title, topic, and content.
"""

from pathlib import Path
from typing import Literal

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_shared.time_utils import get_utc_date_str


# ================================
# --> Tools
# ================================

@agent_tool(name="append_memory")
def append_memory(
    _memory_file: Path,
    title: str,
    topic: Literal[
        "strategy_insights",
        "regime_observations",
        "factor_interactions",
        "macro_signals",
        "research_gaps",
        "past_mistakes",
    ],
    content: str,
) -> str:
    """
    Persist a structured memory entry to your long-term memory file. Use this
    to record learnings, patterns, and insights that should inform future runs.

    Memories survive across sessions — anything written here will be available
    the next time you run. Write concise, actionable entries.

    Args:
        _memory_file: Absolute path to the agent's memory.md (pre-bound).
        title: Short descriptive title for the memory entry.
        topic: Category of the memory entry.
        content: The memory body. Should be concise and actionable.

    Returns:
        Confirmation that the memory was written.

    Examples:
        append_memory(title="Momentum Regime Sensitivity", topic="regime_observations", content="Momentum strategies underperform in choppy regimes.")
        >>> {"success": True, "data": {"title": "Momentum Regime Sensitivity", "topic": "regime_observations"}}

    Raises:
        IOError: If the memory file cannot be written.
    """
    try:
        date = get_utc_date_str()

        entry = (
            f"---\n"
            f"date: {date}\n"
            f"title: {title}\n"
            f"topic: {topic}\n"
            f"---\n"
            f"{content}\n\n"
        )

        with open(_memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

        return success_response({"title": title, "topic": topic, "date": date})

    except Exception as e:
        return error_response(f"Failed to append memory: {e}")



