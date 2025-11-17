"""Retrieve notes tool for BaseAgent v2."""

from pathlib import Path
from typing import Optional
import re
import yaml
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response


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
            return error_response("No notes file found",)

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

        for i, line in enumerate(lines):
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
            elif line.strip() == '---END_NOTE---':
                # New delimiter - always marks end of note
                if in_note and current_title and title.lower() in current_title.lower():
                    matching_notes.append('\n'.join(current_note))
                current_note = []
                current_title = None
                in_note = False
            elif line.strip() == '---':
                # Legacy delimiter - only treat as end marker if followed by blank line or another note
                # This prevents treating markdown horizontal rules (---) as note boundaries
                next_line_idx = i + 1
                is_end_marker = False

                if next_line_idx >= len(lines):
                    # EOF - this is an end marker
                    is_end_marker = True
                elif lines[next_line_idx].strip() == '':
                    # Blank line after --- could be end marker
                    # Check if followed by another note header or EOF
                    peek_idx = next_line_idx + 1
                    if peek_idx >= len(lines) or note_header_pattern.match(lines[peek_idx]):
                        is_end_marker = True

                if is_end_marker:
                    if in_note and current_title and title.lower() in current_title.lower():
                        matching_notes.append('\n'.join(current_note))
                    current_note = []
                    current_title = None
                    in_note = False
                elif in_note:
                    # Not an end marker - include it in the note content
                    current_note.append(line)
            elif in_note:
                current_note.append(line)

        # Check last note
        if in_note and current_title and title.lower() in current_title.lower():
            matching_notes.append('\n'.join(current_note))

        if matching_notes:
            return success_response( {
                    "notes": matching_notes,
                    "count": len(matching_notes),
                },)
        else:
            return error_response(f"No notes found with title containing '{title}'")

    except Exception as e:
        return error_response(str(e),)


RETRIEVE_NOTES_DESCRIPTION = """Retrieves previously stored analysis notes and insights from this run's notes.md file.

**CRITICAL: Use this tool at these specific times:**
1. **START of new analysis phase** - Check for previous work to maintain continuity
2. **Before portfolio construction** - Review thesis, drivers, risk factors from earlier research
3. **Before finalization** - Ensure all previous insights are incorporated into final answer
4. **After every 5-10 tool calls** - Reconnect with earlier findings to maintain coherence
5. **When connecting phases** - Bridge gap between research → analysis → decision making
6. **When you feel you're missing context** - Previous notes may contain critical insights

**Why this matters:**
- Notes contain deep analysis that shouldn't be lost or forgotten
- Prevents repeating expensive API calls and redundant analysis
- Maintains consistency and coherence across long workflows
- Connects insights across different analytical phases
- Ensures final decisions incorporate ALL previous research

**Example workflow:**
Research Phase → write_note("Stock Analysis Findings", content)
[... other work ...]
Analysis Phase → retrieve_notes("Stock Analysis") ← DON'T SKIP THIS
Portfolio Phase → retrieve_notes("Stock Analysis") ← CRITICAL for thesis consistency
Finalization → retrieve_notes("Stock Analysis") ← Ensure nothing is lost

**Technical details:**
- The title parameter must match the title you used in write_note (case-insensitive, partial match)
- Returns all notes whose titles contain the search string
- Use the EXACT SAME title string that was passed to write_note for best results
"""

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

