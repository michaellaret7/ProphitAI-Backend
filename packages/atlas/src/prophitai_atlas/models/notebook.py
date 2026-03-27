from typing import List
from pydantic import BaseModel, Field

from prophitai_shared.time_utils import get_utc_timestamp_str
from typing import Optional

class Note(BaseModel):
    """A notebook for agent execution."""

    title: str = Field(..., description="The title of the notebook")
    content: str = Field(..., description="The content of the notebook")
    worker_task: str = Field(..., description="The task that the worker is performing")
    timestamp: str = Field(..., description="The timestamp of the note")

class Notebook(BaseModel):
    """A notebook for agent execution."""
    notes: List[Note] = Field(default_factory=list, description="The notes in the notebook")

    def add_note(self, title:str, content: str, worker_task: str) -> Note:
        """Add a note to the notebook."""

        note = Note(
            title=title.strip(),
            content=content.strip(),
            worker_task=worker_task.strip(),
            timestamp=get_utc_timestamp_str()
        )

        # Append note model to the notes list
        self.notes.append(note)

        return note

    def get_available_notes(self) -> List[str]:
        """Get the available notes in the notebook."""
        return [f"Title: {note.title}, Timestamp: {note.timestamp}" for note in self.notes]

    def get_notes(self, title_filter: Optional[str] = None) -> List[Note] | str:
        """Get notes, optionally filtered by title. Returns list of Notes or formatted string for LLM.

        Args:
            title_filter: Case-insensitive partial match on note titles.
            formatted: If True, return a readable string instead of Note objects.
        """
        notes = self.notes

        if title_filter:
            query = title_filter.lower()
            notes = [n for n in notes if query in n.title.lower()]

        if not notes:
            return "No notes recorded."

        sections = []
        for i, note in enumerate(notes, 1):
            sections.append(
                f"--- Note {i} ---\n"
                f"Title: {note.title}\n"
                f"Time: {note.timestamp}\n\n"
                f"{note.content}"
            )
        return "\n\n".join(sections)
