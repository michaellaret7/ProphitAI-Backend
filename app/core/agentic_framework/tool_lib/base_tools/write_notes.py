from pathlib import Path
from typing import Optional
import yaml
from app.utils.time_utils import get_utc_timestamp_str


def write_note(title: str, content: str, *, output_dir: Optional[str] = None) -> str:
    """Append a note to the current agent run's notes.md file.

    Args:
        title: Short title for the note
        content: Note body (multiline allowed)
        output_dir: Agent run output directory; if None, writes to ./notes.md

    Returns:
        YAML string with success status and file path
    """
    try:
        notes_path = Path(output_dir) / "notes.md" if output_dir else Path("notes.md")
        if not notes_path.exists():
            # Initialize file with a simple header
            notes_path.write_text("# Notes\n\n", encoding="utf-8")

        timestamp = get_utc_timestamp_str()
        safe_title = (title or "").strip()
        body = (content or "").rstrip()

        entry_lines = [
            f"## {timestamp} - {safe_title}",
            "",
            body,
            "",
            "---END_NOTE---",
            "",
        ]

        with notes_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(entry_lines))

        return yaml.dump({
            "success": True,
            "data": {
                "file": str(notes_path),
                "title": safe_title,
                "timestamp": timestamp,
            },
        }, default_flow_style=False)
    except Exception as e:
        return yaml.dump({
            "success": False,
            "error": str(e),
        }, default_flow_style=False)


WRITE_NOTE_DESCRIPTION = """Write free-form reasoning and analysis to this run's notes.md file.

**When to use:**
- Store detailed research findings, stock analysis, or thesis development
- Capture complex reasoning, hypotheses, alternatives, decisions, and trade-offs
- Document anomalies, key insights, or important calculations
- Save expensive API call results that you might need later
- Record intermediate conclusions before moving to next phase

**IMPORTANT:** Notes you write can be retrieved later using retrieve_notes(title).
Always use clear, descriptive titles so you can easily retrieve them in later phases.

**Example titles:**
- "Stock Screening Results - Consumer Staples"
- "Valuation Analysis - AAPL"
- "Portfolio Thesis and Investment Drivers"
- "Risk Factor Analysis"

Think of this as your persistent memory across the workflow.
"""

WRITE_NOTE_PARAMETERS = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Short title for the note",
        },
        "content": {
            "type": "string",
            "description": "Note body (multiline allowed)",
        },
    },
    "required": ["title", "content"],
}

