"""Tool for updating task status with evidence and reason."""

import yaml
from typing import Dict, Any, Optional
from app.core.agentic_framework.base_agent.tasks.models import TaskStatus


def update_task_status(
    agent,
    task_id: str,
    status: str,
    reason: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None
) -> str:
    """Update the status of a task or subtask with evidence.

    Args:
        agent: BaseAgent instance
        task_id: Task ID as string (int for main task, e.g. '1a' for subtask)
        status: Status string ('started', 'in_progress', 'completed', 'failed', 'blocked')
        reason: Optional reason for status change
        evidence: Optional evidence dict with outputs and observations

    Returns:
        YAML formatted string with success status and task details
    """
    # String to enum mapping
    STATUS_MAP = {
        'started': TaskStatus.IN_PROGRESS,
        'in_progress': TaskStatus.IN_PROGRESS,
        'completed': TaskStatus.COMPLETED,
        'failed': TaskStatus.FAILED,
        'blocked': TaskStatus.BLOCKED
    }

    try:
        # Validate status
        if status not in STATUS_MAP:
            return yaml.dump({
                "success": False,
                "error": f"Invalid status: {status}. Must be one of: {list(STATUS_MAP.keys())}"
            }, default_flow_style=False)

        # Handle main task (numeric ID)
        if task_id.isdigit():
            task_id_int = int(task_id)
            success = agent.task_manager.status.update_main_task(
                task_id_int,
                STATUS_MAP[status],
                reason
            )

            # Add evidence if provided
            if evidence:
                agent.task_manager.evidence.add_evidence(task_id_int, str(evidence))

            # Persist changes
            agent.task_manager.persistence.save_state()

            return yaml.dump({
                "success": success,
                "task_id": task_id,
                "status": status,
                "message": f"Main task {task_id} status updated to {status}"
            }, default_flow_style=False)

        # Handle subtask (e.g., '1a', '2b')
        else:
            # Extract main task ID from subtask ID (first digit)
            main_task_id = int(task_id[0]) if task_id and task_id[0].isdigit() else None

            if not main_task_id:
                return yaml.dump({
                    "success": False,
                    "error": f"Invalid task_id format: {task_id}. Expected numeric (e.g., '1') or subtask format (e.g., '1a')"
                }, default_flow_style=False)

            # For subtasks, 'completed' status sets completed=True
            should_complete = (status == 'completed')
            success = agent.task_manager.status.update_subtask(
                main_task_id,
                task_id,
                should_complete,
                reason
            )

            # Add evidence if provided
            if evidence:
                agent.task_manager.evidence.add_evidence(main_task_id, str(evidence), task_id)

            # Persist changes
            agent.task_manager.persistence.save_state()

            return yaml.dump({
                "success": success,
                "task_id": task_id,
                "status": status,
                "message": f"Subtask {task_id} status updated to {status}"
            }, default_flow_style=False)

    except Exception as e:
        return yaml.dump({
            "success": False,
            "error": f"Failed to update task status: {str(e)}",
            "task_id": task_id
        }, default_flow_style=False)


# Tool Schema Constants
UPDATE_TASK_STATUS_DESCRIPTION = (
    "Update the status of a task or subtask with evidence of completion or progress. "
    "Use this to track task progression and record what has been accomplished. "
    "Supports both main tasks (numeric ID like '1') and subtasks (format like '1a', '2b')."
)

UPDATE_TASK_STATUS_PARAMETERS = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Task identifier (e.g., '1' for main task, '1a' for subtask)"
        },
        "status": {
            "type": "string",
            "enum": ["started", "in_progress", "completed", "failed", "blocked"],
            "description": "New task status"
        },
        "evidence": {
            "type": "object",
            "description": "Evidence supporting the status change",
            "properties": {
                "outputs": {"type": "object", "description": "Task outputs/results"},
                "observations": {"type": "array", "items": {"type": "string"}}
            }
        },
        "reason": {
            "type": "string",
            "description": "Explanation for the status change"
        }
    },
    "required": ["task_id", "status"]
}

UPDATE_TASK_STATUS_TOOL = {
    "name": "update_task_status",
    "description": UPDATE_TASK_STATUS_DESCRIPTION,
    "parameters": UPDATE_TASK_STATUS_PARAMETERS,
    "function": update_task_status,
}
