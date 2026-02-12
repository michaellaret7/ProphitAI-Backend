from app.core.atlas.models.notebook import Notebook
from app.core.atlas.tools.responses import success_response, error_response

def write_note(
    notebook: Notebook,
    title: str,
    content: str,
    worker_task: str,
) -> str:
    """Write a note to the shared orchestrator notebook.

    Args:
        notebook: Shared Notebook instance (pre-bound via partial).
        title: Short descriptive title for the note.
        content: Note body with findings, analysis, or insights.
        worker_task: The worker's task description (pre-bound via partial).

    Returns:
        YAML success/error response string.
    """
    try:
        note = notebook.add_note(title=title, content=content, worker_task=worker_task)
        return success_response({
            "title": note.title,
            "timestamp": note.timestamp,
            "total_notes": len(notebook.notes),
        })
    except Exception as e:
        return error_response(f"Failed to write note: {e}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

WRITE_NOTE_DESCRIPTION = (
    "Write supporting data, evidence, and analysis to the shared notebook for the "
    "orchestrator to reference later.\n\n"
    "**CRITICAL — Notes are supplementary, NOT a copy of your final answer.**\n"
    "Your final answer is your summary and conclusions. Notes are the raw evidence, "
    "detailed data, and supporting analysis behind those conclusions. The orchestrator "
    "reads your final answer first, then pulls notes only when it needs deeper context. "
    "If notes just repeat your final answer, they add zero value.\n\n"
    "**What belongs in notes (NOT in your final answer):**\n"
    "- Raw data tables, specific numbers, and detailed metrics from tool calls\n"
    "- Full reasoning chains and intermediate calculations\n"
    "- Edge cases, caveats, anomalies, and risks you discovered\n"
    "- Alternative interpretations or hypotheses you considered\n"
    "- Verbatim quotes or passages from earnings calls, filings, or research\n\n"
    "**What belongs in your final answer (NOT in notes):**\n"
    "- High-level conclusions, recommendations, and key takeaways\n"
    "- Direct answers to the task you were assigned\n\n"
    "**Think of it this way:** Your final answer is the executive summary. "
    "Notes are the appendix. Never duplicate between the two.\n\n"
    "**Tips:**\n"
    "- Use clear, descriptive titles (e.g., 'AAPL Q4 Revenue Breakdown - Raw Data')\n"
    "- Write multiple focused notes rather than one massive note\n"
    "- Write notes as you go, not all at the end"
)

WRITE_NOTE_PARAMETERS = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Short descriptive title for the note (e.g., 'AAPL Earnings Summary')",
        },
        "content": {
            "type": "string",
            "description": "Note body with findings, analysis, or insights. Multiline allowed.",
        },
    },
    "required": ["title", "content"],
    "additionalProperties": False,
}

# Reason: `function` is intentionally omitted — it must be bound via
# functools.partial(write_note, notebook, worker_task=task) at registration time.
WRITE_NOTE_TOOL = {
    "name": "write_note",
    "description": WRITE_NOTE_DESCRIPTION,
    "parameters": WRITE_NOTE_PARAMETERS,
}

