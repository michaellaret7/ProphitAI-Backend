"""Retrieve notes tool for BaseAgent v2."""

from pathlib import Path
from typing import Optional
import re
import yaml


def retrieve_notes(title: str, *, output_dir: Optional[str] = None) -> str:
    """Retrieve notes from the current agent run's notes.md file.

    Args:
        title: Title of the note to retrieve (searches for matching sections)
        output_dir: Agent run output directory; if None, reads from ./notes.md

    Returns:
        YAML string with success status and note content
    """
    try:
        notes_path = Path(output_dir) / "notes.md" if output_dir else Path("notes.md")
        if not notes_path.exists():
            return yaml.dump({
                "success": False,
                "error": "No notes file found",
            }, default_flow_style=False)

        # Read the entire notes file
        content = notes_path.read_text(encoding="utf-8")

        # Search for notes with matching title
        # Note headers follow format: ## YYYY-MM-DDTHH:MM:SS... - Title
        # Regular markdown headers (## Title) should NOT be treated as note boundaries
        matching_notes = []
        lines = content.split('\n')
        current_note = []
        current_title = None
        in_note = False

        # Pattern to match note headers with ISO timestamp
        # Format: ## 2025-11-05T15:28:10.561460+00:00 - Title
        note_header_pattern = re.compile(r'^##\s+\d{4}-\d{2}-\d{2}T[\d:\.+\-]+\s+-\s+(.+)$')

        for line in lines:
            # Check for note header (## timestamp - title)
            match = note_header_pattern.match(line)
            if match:
                # Save previous note if it matches
                if in_note and current_title and title.lower() in current_title.lower():
                    matching_notes.append('\n'.join(current_note))

                # Start new note
                current_note = [line]
                current_title = match.group(1)  # Extract title from regex match
                in_note = True
            elif line.strip() == '---':
                # End of note
                if in_note and current_title and title.lower() in current_title.lower():
                    matching_notes.append('\n'.join(current_note))
                current_note = []
                current_title = None
                in_note = False
            elif in_note:
                current_note.append(line)

        # Check last note
        if in_note and current_title and title.lower() in current_title.lower():
            matching_notes.append('\n'.join(current_note))

        if matching_notes:
            return yaml.dump({
                "success": True,
                "data": {
                    "notes": matching_notes,
                    "count": len(matching_notes),
                },
            }, default_flow_style=False)
        else:
            return yaml.dump({
                "success": False,
                "error": f"No notes found with title containing '{title}'",
            }, default_flow_style=False)

    except Exception as e:
        return yaml.dump({
            "success": False,
            "error": str(e),
        }, default_flow_style=False)


RETRIEVE_NOTES_DESCRIPTION = (
    "Retrieve notes from this run's notes.md file by searching for a title. "
    "CRITICAL: The title parameter must EXACTLY match the title you used when calling write_note. "
    "Use the EXACT SAME title string that was passed to write_note's 'title' parameter. "
    "The search is case-insensitive and matches partial titles, but you should use the exact title "
    "from write_note for best results. Returns all notes whose titles contain the search string."
)

RETRIEVE_NOTES_PARAMETERS = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": (
                "MUST be the EXACT title you used when calling write_note. "
                "Use the same string you passed to write_note's 'title' parameter. "
                "Search is case-insensitive and matches partial titles."
            ),
        },
    },
    "required": ["title"],
}

# Test code - output_dir should be the directory path, NOT the full file path
output_dir = "/Users/michaellaret/Desktop/ProphitAI/agent_output/2025-11-05/BaseAgent_152643"

if __name__ == "__main__":
    print(retrieve_notes(title="AAPL Individual Analysis - Performance and Risk Profile", output_dir=output_dir))