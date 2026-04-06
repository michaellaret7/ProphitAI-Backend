"""Append-only memory tool for fund agents.

Writes content to a per-agent memory.md file. The file path is
pre-bound via functools.partial at agent init time — the LLM only
sees the ``content`` parameter.
"""

from pathlib import Path

from prophitai_atlas.tools.responses import success_response, error_response


def append_memory(memory_file: Path, content: str) -> str:
    """Append a memory entry to the agent's memory file.

    Args:
        memory_file: Absolute path to the agent's memory.md (pre-bound).
        content: The memory entry to persist.

    Returns:
        YAML success/error response string.
    """
    try:
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(f"{content}\n\n")

        return success_response({"wrote_to": str(memory_file)})

    except Exception as e:
        return error_response(f"Failed to append memory: {e}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

APPEND_MEMORY_DESCRIPTION = (
    "Persist a memory entry to your long-term memory file. Use this to record "
    "learnings, patterns, and insights that should inform future runs.\n\n"
    "Memories survive across sessions — anything written here will be available "
    "the next time you run. Write concise, actionable entries."
)

APPEND_MEMORY_PARAMETERS = {
    "type": "object",
    "properties": {
        "content": {
            "type": "string",
            "description": "The memory entry to persist. Should be concise and actionable.",
        },
    },
    "required": ["content"],
    "additionalProperties": False,
}

# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(append_memory, memory_file) at registration time.
APPEND_MEMORY_TOOL = {
    "name": "append_memory",
    "description": APPEND_MEMORY_DESCRIPTION,
    "parameters": APPEND_MEMORY_PARAMETERS,
}
