"""Tool for marking tasks as complete with outputs and summary."""

import yaml
from typing import Dict, Any, Optional
from app.core.agentic_framework.base_agent.tasks.models import TaskStatus


def mark_task_complete(
    agent,
    task_id: str,
    summary: Optional[str] = None,
    outputs: Optional[Dict[str, Any]] = None
) -> str:
    """Mark a main task as complete with optional outputs and summary.

    Args:
        agent: BaseAgent instance
        task_id: Main task ID as string (must be numeric, e.g., '1', '2')
        summary: Optional summary of what was accomplished
        outputs: Optional outputs/results dict from the task

    Returns:
        YAML formatted string with success status and task details
    """
    try:
        # Validate task_id is numeric (only works for main tasks)
        if not task_id.isdigit():
            return yaml.dump({
                "success": False,
                "error": f"Task ID must be numeric for mark_complete (e.g., '1', '2'). Got: {task_id}. "
                        f"Use update_task_status for subtasks."
            }, default_flow_style=False)

        task_id_int = int(task_id)

        # BUG FIX: Validate all subtasks are complete before marking task complete
        # This prevents agents from bypassing plan execution by manually completing tasks
        plan = agent.execution_engine.get_current_structured_plan()
        if plan:
            for task in plan.tasks:
                if task.id == task_id_int:
                    if task.subtasks:
                        incomplete_subtasks = [st for st in task.subtasks if not st.completed]
                        if incomplete_subtasks:
                            incomplete_ids = [st.id for st in incomplete_subtasks]
                            return yaml.dump({
                                "success": False,
                                "error": f"Cannot mark task {task_id} complete: {len(incomplete_subtasks)} subtask(s) still incomplete",
                                "incomplete_subtasks": incomplete_ids,
                                "suggestion": "Complete all subtasks before marking task complete, or use get_current_task_info to check status",
                                "task_id": task_id
                            }, default_flow_style=False)
                    break

        # Update task status to completed
        success = agent.task_manager.status.update_main_task(
            task_id_int,
            TaskStatus.COMPLETED,
            summary
        )

        if not success:
            return yaml.dump({
                "success": False,
                "error": f"Failed to mark task {task_id} as complete. Task may not exist.",
                "task_id": task_id
            }, default_flow_style=False)

        # Add evidence if summary or outputs provided
        if outputs or summary:
            evidence_str = f"Completed: {summary or 'No summary'}"
            if outputs:
                evidence_str += f" | Outputs: {outputs}"
            agent.task_manager.evidence.add_evidence(task_id_int, evidence_str)

        # Persist changes
        agent.task_manager.persistence.save_state()

        return yaml.dump({
            "success": True,
            "task_id": task_id,
            "status": "completed",
            "message": f"Task {task_id} marked as complete",
            "summary": summary,
            "has_outputs": bool(outputs)
        }, default_flow_style=False)

    except Exception as e:
        return yaml.dump({
            "success": False,
            "error": f"Failed to mark task complete: {str(e)}",
            "task_id": task_id
        }, default_flow_style=False)


# Tool Schema Constants
MARK_TASK_COMPLETE_DESCRIPTION = (
    "Mark a main task as complete with optional outputs and summary. "
    "This is a convenience tool for marking tasks done with final results. "
    "Only works for main tasks (numeric IDs like '1', '2'). Use update_task_status for subtasks."
)

MARK_TASK_COMPLETE_PARAMETERS = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Main task identifier (must be numeric, e.g., '1', '2')"
        },
        "outputs": {
            "type": "object",
            "description": "Task outputs/results dictionary"
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of what was accomplished"
        }
    },
    "required": ["task_id"]
}

MARK_TASK_COMPLETE_TOOL = {
    "name": "mark_task_complete",
    "description": MARK_TASK_COMPLETE_DESCRIPTION,
    "parameters": MARK_TASK_COMPLETE_PARAMETERS,
    "function": mark_task_complete,
}
