"""Notes file utilities for BaseAgent v2 runs."""

from pathlib import Path
from typing import Optional
from app.utils.time_utils import get_current_utc_time


def ensure_notes_file(output_dir: Optional[str], agent_name: str) -> Path:
    """Ensure notes.md exists in the run directory with a header.

    Args:
        output_dir: Directory path for the current agent run
        agent_name: Logical name of the agent (for header)

    Returns:
        Path to the notes.md file
    """
    notes_path = Path(output_dir) / "notes.md" if output_dir else Path("notes.md")
    if not notes_path.exists():
        header = (
            f"# Notes for {agent_name}\n\n"
            f"Created: {get_current_utc_time().isoformat()} UTC\n\n"
        )
        notes_path.write_text(header, encoding="utf-8")
    return notes_path


