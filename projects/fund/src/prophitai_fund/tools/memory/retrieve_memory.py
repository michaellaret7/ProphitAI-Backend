"""Read-only memory retrieval tool for fund agents.

Parses the per-agent memory.md file and returns all structured entries.
The file path is pre-bound via functools.partial — the LLM sees no parameters.
"""

import re
from pathlib import Path
from typing import List, Dict

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Helper funcs
# ================================

def _parse_memories(memory_file: Path) -> List[Dict[str, str]]:
    """Parse memory.md into a list of structured entries.

    Each entry has keys: date, title, topic, content.
    """
    text = memory_file.read_text(encoding="utf-8").strip()

    if not text:
        return []

    # Reason: match complete frontmatter blocks (---\n...\n---) followed by content
    pattern = re.compile(r"^---\n(.*?)\n---\n(.*?)(?=\n^---\n|\Z)", flags=re.DOTALL | re.MULTILINE)
    entries: List[Dict[str, str]] = []

    for match in pattern.finditer(text):
        frontmatter = match.group(1)
        content = match.group(2).strip()

        entry: Dict[str, str] = {"content": content}

        for line in frontmatter.strip().splitlines():
            key, _, value = line.partition(":")

            if value:
                entry[key.strip()] = value.strip()

        entries.append(entry)

    return entries


# ================================
# --> Tools
# ================================

@agent_tool(name="retrieve_memory")
def retrieve_memory(_memory_file: Path) -> str:
    """
    Retrieve all entries from your long-term memory file. Returns every
    memory you have previously saved, with date, title, topic, and content.

    Call this at the start of a run to recall past learnings before
    beginning new research.

    Args:
        _memory_file: Absolute path to the agent's memory.md (pre-bound).

    Returns:
        List of all memory entries with date, title, topic, and content.

    Examples:
        retrieve_memory()
        >>> {"success": True, "data": {"count": 2, "memories": [...]}}
    """
    try:
        if not _memory_file.exists():
            return success_response({"count": 0, "memories": []})

        entries = _parse_memories(_memory_file)

        return success_response({"count": len(entries), "memories": entries})

    except Exception as e:
        return error_response(f"Failed to retrieve memories: {e}")
