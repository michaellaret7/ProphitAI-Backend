"""Worker notes tool - writes structured notes to orchestrator-managed memory."""

from typing import Any, Callable, Dict

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.time_utils import get_utc_timestamp_str

WORKER_WRITE_NOTE_DESCRIPTION = """Write an in-memory note for the orchestrator to review later.

Use this after meaningful discoveries, intermediate conclusions, or risks.
Keep notes concise and specific so the orchestrator can quickly synthesize them.
"""

WORKER_WRITE_NOTE_PARAMETERS = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Short note title",
        },
        "content": {
            "type": "string",
            "description": "Detailed note content",
        },
    },
    "required": ["title", "content"],
    "additionalProperties": False,
}


def create_worker_write_note_tool(
    *,
    worker_id: str,
    worker_task: str,
    note_sink: Callable[[Dict[str, Any]], None],
) -> Dict[str, Any]:
    """Create a worker-local write_note tool bound to orchestrator note storage."""

    def write_note(title: str, content: str) -> str:
        try:
            safe_title = (title or "").strip()
            body = (content or "").strip()

            if not safe_title:
                return error_response("title must be a non-empty string")
            if not body:
                return error_response("content must be a non-empty string")

            note = {
                "worker_id": worker_id,
                "task": worker_task,
                "title": safe_title,
                "content": body,
                "timestamp": get_utc_timestamp_str(),
            }
            note_sink(note)

            return success_response(
                {
                    "worker_id": worker_id,
                    "title": safe_title,
                    "timestamp": note["timestamp"],
                }
            )
        except Exception as exc:
            return error_response(exc)

    return {
        "name": "write_note",
        "description": WORKER_WRITE_NOTE_DESCRIPTION,
        "parameters": WORKER_WRITE_NOTE_PARAMETERS,
        "function": write_note,
    }
