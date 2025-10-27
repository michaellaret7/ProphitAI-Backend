"""Task Management Tool - Update plan task statuses during execution."""

from typing import List, Optional, Dict, Any
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus


def update_tasks(
    plan,
    main_task: str,
    subtasks: Optional[List[str]] = None,
    status: str = "in_progress"
) -> Dict[str, Any]:
    """Update the status of tasks and subtasks in the plan.

    Args:
        plan: The agent's plan object
        main_task: The main task ID to update (e.g., "1", "2", "3")
        subtasks: Optional list of subtask IDs to update (e.g., ["1a", "1b"])
        status: New status - "not_started", "in_progress", or "complete"

    Returns:
        Dictionary with success status and updated tasks

    Examples:
        update_tasks(plan, main_task="4", subtasks=["4a", "4b"], status="complete")
        update_tasks(plan, main_task="5", status="in_progress")
    """
    if not plan or not plan.tasks:
        return {
            "success": False,
            "error": "No plan available to update"
        }

    # Normalize status string to enum
    status_map = {
        "not_started": TaskStatus.NOT_STARTED,
        "not started": TaskStatus.NOT_STARTED,
        "in_progress": TaskStatus.IN_PROGRESS,
        "in progress": TaskStatus.IN_PROGRESS,
        "complete": TaskStatus.COMPLETE,
        "completed": TaskStatus.COMPLETE
    }

    status_enum = status_map.get(status.lower())
    if not status_enum:
        return {
            "success": False,
            "error": f"Invalid status: {status}. Must be one of: not_started, in_progress, complete"
        }

    # Find the main task
    task = next((t for t in plan.tasks if t.id == main_task), None)
    if not task:
        return {
            "success": False,
            "error": f"Task {main_task} not found in plan"
        }

    updated = []

    # Update main task status
    old_status = task.status.value
    task.status = status_enum
    updated.append(f"Task {main_task}: {old_status} → {status_enum.value}")

    # Update subtasks if provided
    if subtasks:
        for subtask_id in subtasks:
            subtask = next((st for st in task.subtasks if st.id == subtask_id), None)
            if subtask:
                old_st_status = subtask.status.value
                subtask.status = status_enum
                updated.append(f"Subtask {subtask_id}: {old_st_status} → {status_enum.value}")
            else:
                updated.append(f"⚠️ Subtask {subtask_id} not found in task {main_task}")

    return {
        "success": True,
        "updated": updated,
        "message": f"Successfully updated {len(updated)} item(s)"
    }


# Tool schema for agent registration
UPDATE_TASKS_DESCRIPTION = """Update the status of tasks and subtasks in your execution plan.

Use this tool to track your progress as you work through the plan:
- Mark tasks as "in_progress" when you start working on them
- Mark tasks as "complete" when you finish them
- You can update both the main task and its subtasks in a single call

This helps maintain an accurate view of what's been done and what remains."""

UPDATE_TASKS_PARAMETERS = {
    "type": "object",
    "properties": {
        "main_task": {
            "type": "string",
            "description": "The main task ID to update (e.g., '1', '2', '3')"
        },
        "subtasks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of subtask IDs to update (e.g., ['1a', '1b'])"
        },
        "status": {
            "type": "string",
            "enum": ["not_started", "in_progress", "complete"],
            "description": "New status for the task(s). Use 'in_progress' when starting, 'complete' when finished."
        }
    },
    "required": ["main_task", "status"]
}
