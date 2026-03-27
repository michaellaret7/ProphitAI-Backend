"""Retrieve notes tool - lets the orchestrator review worker-written notes."""

from typing import Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_atlas.models.notebook import Notebook


# ================================
# --> Tools
# ================================

@agent_tool(name="retrieve_notes")
def retrieve_notes(
    _notebook: Notebook,
    title_filter: Optional[str] = None,
) -> str:
    """Review notes written by worker agents during this run. Workers write notes
containing raw data, detailed evidence, and supporting analysis that is NOT
included in their final answers.

**Two ways to call this tool:**

1. **No arguments** → `retrieve_notes()`
   Returns a table of contents listing every note with its title, which worker
   wrote it, and when. Use this first to see what's available before pulling
   specific notes.

2. **With title_filter** → `retrieve_notes(title_filter='AAPL')`
   Returns the full content of all notes whose titles contain the filter string.
   The search is case-insensitive and matches partial titles.

    Args:
        title_filter: Case-insensitive partial match on note titles.
            Omit to get a table of contents of all available notes.
            Provide to get full content of matching notes.
    """
    try:
        if not _notebook.notes:
            return success_response("No worker notes recorded yet.")

        if title_filter is None:
            return success_response({
                "total_notes": len(_notebook.notes),
                "available_notes": _notebook.get_available_notes(),
            })

        notes = _notebook.get_notes(title_filter=title_filter)
        return success_response(notes)

    except Exception as e:
        return error_response(f"Failed to retrieve notes: {e}")


# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(retrieve_notes, notebook) at registration time.
RETRIEVE_NOTES_TOOL = {k: v for k, v in retrieve_notes.tool.items() if k != "function"}
