"""Review worker notes tool - query orchestrator's in-memory worker notes."""

from typing import Any, Dict, List, Optional, Callable

from app.core.atlas.tools.responses import success_response

REVIEW_WORKER_NOTES_DESCRIPTION = """Review notes written by worker agents during this run.

Use this to inspect findings before synthesis, retrying workers, or updating plans.
Filter by worker_id or title keywords and keep limit small for context efficiency.
"""

REVIEW_WORKER_NOTES_PARAMETERS = {
    "type": "object",
    "properties": {
        "worker_id": {
            "type": "string",
            "description": "Optional worker id filter (e.g., 'worker-1').",
        },
        "title_contains": {
            "type": "string",
            "description": "Optional case-insensitive keyword filter on note title.",
        },
        "limit": {
            "type": "integer",
            "description": "Max notes to return (most recent matching notes). Default 10.",
            "minimum": 1,
            "maximum": 100,
        },
        "include_content": {
            "type": "boolean",
            "description": "Set false to return only note metadata.",
        },
    },
    "additionalProperties": False,
}


def _filter_worker_notes(
    notes: List[Dict[str, Any]],
    *,
    worker_id: Optional[str] = None,
    title_contains: Optional[str] = None,
    limit: int = 10,
    include_content: bool = True,
) -> Dict[str, Any]:
    """Filter and shape worker notes for orchestrator review."""
    normalized_title = (title_contains or "").strip().lower()

    matching = []
    for note in notes:
        if worker_id and note.get("worker_id") != worker_id:
            continue
        if normalized_title and normalized_title not in (note.get("title", "").lower()):
            continue
        matching.append(note)

    selected = matching[-limit:]
    if not include_content:
        selected = [
            {
                "worker_id": note.get("worker_id"),
                "task": note.get("task"),
                "title": note.get("title"),
                "timestamp": note.get("timestamp"),
            }
            for note in selected
        ]

    return {
        "total_notes": len(notes),
        "matching_notes": len(matching),
        "returned_notes": len(selected),
        "notes": selected,
    }


def create_review_worker_notes_tool(
    notes_provider: Callable[[], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Create a review_worker_notes tool bound to orchestrator note state."""

    def review_worker_notes(
        worker_id: Optional[str] = None,
        title_contains: Optional[str] = None,
        limit: int = 10,
        include_content: bool = True,
    ) -> str:
        notes = notes_provider()
        payload = _filter_worker_notes(
            notes,
            worker_id=worker_id,
            title_contains=title_contains,
            limit=limit,
            include_content=include_content,
        )
        return success_response(payload)

    return {
        "name": "review_worker_notes",
        "description": REVIEW_WORKER_NOTES_DESCRIPTION,
        "parameters": REVIEW_WORKER_NOTES_PARAMETERS,
        "function": review_worker_notes,
    }
