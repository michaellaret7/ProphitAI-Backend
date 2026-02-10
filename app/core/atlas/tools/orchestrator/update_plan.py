"""Update Plan Tool - Mark orchestrator plan tasks as complete."""

from app.core.atlas.models.new_plan import Plan, TaskStatus
from app.core.atlas.tools.responses import success_response, error_response


def update_plan(plan: Plan, task_id: str) -> str:
    """Mark a plan task as complete.

    Args:
        plan: The orchestrator's Plan object.
        task_id: The task ID to mark complete (e.g., "1", "2").

    Returns:
        YAML-formatted success/error response with progress summary.
    """
    if not plan or not plan.tasks:
        return error_response("No plan available to update")

    task = next((t for t in plan.tasks if t.id == task_id), None)
    if not task:
        available = [t.id for t in plan.tasks]
        return error_response(f"Task '{task_id}' not found. Available: {available}")

    if task.status == TaskStatus.COMPLETE:
        return error_response(f"Task {task_id} is already complete.")

    task.status = TaskStatus.COMPLETE

    completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETE)
    total = len(plan.tasks)
    remaining = [
        f"  {t.id}. {t.description}"
        for t in plan.tasks if t.status != TaskStatus.COMPLETE
    ]

    summary = f"Task {task_id} marked complete. Progress: {completed}/{total}."
    if remaining:
        summary += f"\n\nRemaining tasks:\n" + "\n".join(remaining)
    else:
        summary += "\n\nAll tasks complete — synthesize your final answer now."

    return success_response({"message": summary})


UPDATE_PLAN_DESCRIPTION = (
    "Mark a plan task as complete after a worker has finished it. "
    "Call this after each deploy_worker_agent returns successfully.\n\n"
    "Example: update_plan(task_id='1')  # after worker finishes task 1"
)

UPDATE_PLAN_PARAMETERS = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "The task ID to mark as complete (e.g., '1', '2', '3')"
        },
    },
    "required": ["task_id"],
}

UPDATE_PLAN_TOOL = {
    "name": "update_plan",
    "description": UPDATE_PLAN_DESCRIPTION,
    "parameters": UPDATE_PLAN_PARAMETERS,
    "function": update_plan,
}
