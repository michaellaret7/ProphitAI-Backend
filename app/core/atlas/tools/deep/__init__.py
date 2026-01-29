"""Deep-only tools for DeepAgent - planning, notes, and finalization."""

from .finalize import (
    finalize,
    FINALIZE_DESCRIPTION,
    FINALIZE_PARAMETERS,
)
from .edit_plan import (
    edit_plan,
    create_edit_plan_wrapper,
    EDIT_PLAN_DESCRIPTION,
    EDIT_PLAN_PARAMETERS,
    EDIT_PLAN_TOOL,
)
from .update_task import (
    update_tasks,
    UPDATE_TASKS_DESCRIPTION,
    UPDATE_TASKS_PARAMETERS,
)
from .write_notes import (
    write_note,
    WRITE_NOTE_DESCRIPTION,
    WRITE_NOTE_PARAMETERS,
)
from .retrieve_notes import (
    retrieve_notes,
    RETRIEVE_NOTES_DESCRIPTION,
    RETRIEVE_NOTES_PARAMETERS,
)

__all__ = [
    # Finalize
    "finalize",
    "FINALIZE_DESCRIPTION",
    "FINALIZE_PARAMETERS",
    # Edit plan
    "edit_plan",
    "create_edit_plan_wrapper",
    "EDIT_PLAN_DESCRIPTION",
    "EDIT_PLAN_PARAMETERS",
    "EDIT_PLAN_TOOL",
    # Update tasks
    "update_tasks",
    "UPDATE_TASKS_DESCRIPTION",
    "UPDATE_TASKS_PARAMETERS",
    # Write notes
    "write_note",
    "WRITE_NOTE_DESCRIPTION",
    "WRITE_NOTE_PARAMETERS",
    # Retrieve notes
    "retrieve_notes",
    "RETRIEVE_NOTES_DESCRIPTION",
    "RETRIEVE_NOTES_PARAMETERS",
]
