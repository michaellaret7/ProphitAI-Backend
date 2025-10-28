"""Task Management Tool - Update plan task statuses during execution."""

from typing import List, Optional, Dict, Any
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus
from app.core.agentic_framework.base_agent_v2.logging.task_state_logger import write_task_state_to_file


def update_tasks(
    plan,
    main_task: str,
    subtasks: Optional[List[str]] = None,
    status: str = "in_progress",
    work_summary: Optional[str] = None
) -> Dict[str, Any]:
    """Update the status of tasks and subtasks in the plan.

    Args:
        plan: The agent's plan object
        main_task: The main task ID to update (e.g., "1", "2", "3")
        subtasks: Optional list of subtask IDs to update (e.g., ["1a", "1b"])
        status: New status - "not_started", "in_progress", or "complete"
        work_summary: REQUIRED when marking complete - substantive summary of work done (min 100 chars)

    Returns:
        Dictionary with success status and updated tasks

    Examples:
        update_tasks(plan, main_task="4", subtasks=["4a", "4b"], status="complete",
                    work_summary="Analyzed portfolio concentration and identified 65% exposure to Technology sector...")
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

    # Validate work_summary when marking complete
    MIN_WORK_SUMMARY_LENGTH = 100
    if status_enum == TaskStatus.COMPLETE:
        if not work_summary or work_summary.strip() == "":
            return {
                "success": False,
                "error": "WORK EVIDENCE REQUIRED: You must provide a 'work_summary' parameter when marking tasks as complete. This should describe what you actually did and what you found/concluded."
            }

        if len(work_summary.strip()) < MIN_WORK_SUMMARY_LENGTH:
            return {
                "success": False,
                "error": f"INSUFFICIENT WORK EVIDENCE: work_summary must be at least {MIN_WORK_SUMMARY_LENGTH} characters. You provided {len(work_summary.strip())} characters. Please provide a substantive summary of the work you completed."
            }

        # Check for lazy/gaming attempts
        lazy_phrases = ["done", "completed", "finished", "task complete", "all set"]
        if work_summary.strip().lower() in lazy_phrases:
            return {
                "success": False,
                "error": "INSUFFICIENT WORK EVIDENCE: work_summary appears to be a placeholder. Please provide a substantive summary describing what analysis you performed, what data you examined, and what conclusions you reached."
            }

    # Find the main task
    task = next((t for t in plan.tasks if t.id == main_task), None)
    if not task:
        return {
            "success": False,
            "error": f"Task {main_task} not found in plan"
        }

    updated = []

    # Update subtasks if provided
    if subtasks:
        for subtask_id in subtasks:
            subtask = next((st for st in task.subtasks if st.id == subtask_id), None)
            if subtask:
                old_st_status = subtask.status.value
                subtask.status = status_enum

                # Store work summary if marking complete
                if status_enum == TaskStatus.COMPLETE and work_summary:
                    subtask.work_summary = work_summary.strip()
                    updated.append(f"Subtask {subtask_id}: {old_st_status} → {status_enum.value} (with work evidence)")
                else:
                    updated.append(f"Subtask {subtask_id}: {old_st_status} → {status_enum.value}")
            else:
                updated.append(f"⚠️ Subtask {subtask_id} not found in task {main_task}")

        # Auto-update main task status based on subtasks
        if task.subtasks:
            # If any subtask is in progress, mark main task as in progress
            if status_enum == TaskStatus.IN_PROGRESS and task.status == TaskStatus.NOT_STARTED:
                task.status = TaskStatus.IN_PROGRESS
                updated.append(f"✅ Task {main_task}: not started → in progress (subtask started)")

            # If all subtasks are complete, mark main task as complete
            elif all(st.status == TaskStatus.COMPLETE for st in task.subtasks):
                if task.status != TaskStatus.COMPLETE:
                    old_main_status = task.status.value
                    task.status = TaskStatus.COMPLETE
                    task.work_summary = work_summary.strip() if work_summary else "All subtasks completed"
                    updated.append(f"✅ Task {main_task}: {old_main_status} → complete (all subtasks complete)")

    # Update main task only if no subtasks were specified
    else:
        # If marking main task complete, ensure all subtasks are complete
        if status_enum == TaskStatus.COMPLETE and task.subtasks:
            incomplete_subtasks = [st for st in task.subtasks if st.status != TaskStatus.COMPLETE]
            if incomplete_subtasks:
                incomplete_ids = [st.id for st in incomplete_subtasks]
                return {
                    "success": False,
                    "error": f"Cannot mark task {main_task} as complete: subtasks {incomplete_ids} are not yet complete. Complete all subtasks first."
                }

        old_status = task.status.value
        task.status = status_enum

        # Store work summary if marking complete
        if status_enum == TaskStatus.COMPLETE and work_summary:
            task.work_summary = work_summary.strip()
            updated.append(f"Task {main_task}: {old_status} → {status_enum.value} (with work evidence)")
        else:
            updated.append(f"Task {main_task}: {old_status} → {status_enum.value}")

    # Log the updated plan state to file
    try:
        write_task_state_to_file(plan)
    except Exception as e:
        # Don't fail the update if logging fails
        print(f"⚠️  Warning: Failed to write task state to file: {e}")

    return {
        "success": True,
        "updated": updated,
        "message": f"Successfully updated {len(updated)} item(s)"
    }


# Tool schema for agent registration
UPDATE_TASKS_DESCRIPTION = """Update the status of tasks and subtasks in your execution plan.

Use this tool to track your progress as you work through the plan:
- Mark tasks as "in_progress" when you start working on them
- Mark tasks as "complete" when you finish them - **REQUIRES work_summary parameter**
- You can update both the main task and its subtasks in a single call

**IMPORTANT:** When marking tasks as "complete", you MUST provide a work_summary parameter (minimum 100 characters) describing:
  - What analysis you performed
  - What data/tools you used
  - What you discovered or concluded
  - Key findings or decisions made

This prevents marking tasks complete without actually doing the work."""

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
        },
        "work_summary": {
            "type": "string",
            "description": "REQUIRED when status='complete'. Substantive summary (min 100 chars) describing what work was done, what data was analyzed, what was discovered/concluded. Example: 'Analyzed portfolio concentration using portfolio_industry_concentration tool. Found 65% exposure to Technology sector (NVDA, AAPL, MSFT). Identified concentration risk and recommended diversification into Healthcare and Financials.'"
        }
    },
    "required": ["main_task", "status"]
}
