"""Retrieve notes tool - lets the orchestrator review worker-written notes."""

from typing import Optional

from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools.responses import success_response, error_response

def retrieve_notes(
    notebook: Notebook,
    title_filter: Optional[str] = None,
) -> str:
    """Retrieve notes written by worker agents during this run.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        title_filter: Optional case-insensitive partial match on note titles.
            If omitted, returns a table of contents of all available notes.
            If provided, returns the full content of matching notes.

    Returns:
        YAML success/error response string.
    """
    try:
        if not notebook.notes:
            return success_response("No worker notes recorded yet.")

        # Reason: No filter → return lightweight index so orchestrator can decide
        # which notes to pull. With filter → return full content of matching notes.
        if title_filter is None:
            return success_response({
                "total_notes": len(notebook.notes),
                "available_notes": notebook.get_available_notes(),
            })

        notes = notebook.get_notes(title_filter=title_filter)
        return success_response(notes)

    except Exception as e:
        return error_response(f"Failed to retrieve notes: {e}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

RETRIEVE_NOTES_DESCRIPTION = (
    "Review notes written by worker agents during this run. Workers write notes "
    "containing raw data, detailed evidence, and supporting analysis that is NOT "
    "included in their final answers.\n\n"
    "**Two ways to call this tool:**\n\n"
    "1. **No arguments** → `retrieve_notes()`\n"
    "   Returns a table of contents listing every note with its title, which worker "
    "wrote it, and when. Use this first to see what's available before pulling "
    "specific notes.\n\n"
    "2. **With title_filter** → `retrieve_notes(title_filter='AAPL')`\n"
    "   Returns the full content of all notes whose titles contain the filter string. "
    "The search is case-insensitive and matches partial titles. For example, "
    "'revenue' matches 'AAPL Revenue Breakdown', 'Revenue Growth Analysis', etc.\n\n"
    "**Recommended workflow:**\n"
    "- After a worker completes, call `retrieve_notes()` to see the index\n"
    "- Read the worker's final answer first (it has the conclusions)\n"
    "- Pull specific notes only when you need deeper evidence or raw data behind "
    "a conclusion"
)

RETRIEVE_NOTES_PARAMETERS = {
    "type": "object",
    "properties": {
        "title_filter": {
            "type": "string",
            "description": (
                "Case-insensitive partial match on note titles. "
                "Omit to get a table of contents of all available notes. "
                "Provide to get full content of matching notes."
            ),
        },
    },
    "required": [],
    "additionalProperties": False,
}

# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(retrieve_notes, notebook) at registration time.
RETRIEVE_NOTES_TOOL = {
    "name": "retrieve_notes",
    "description": RETRIEVE_NOTES_DESCRIPTION,
    "parameters": RETRIEVE_NOTES_PARAMETERS,
}
