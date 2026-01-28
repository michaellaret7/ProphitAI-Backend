"""Plan progress tracking utilities."""

from typing import Optional
from app.core.atlas.models import Plan, TaskStatus


def get_plan_progress(plan: Optional[Plan]) -> tuple[str, bool]:
    """Check if all tasks in the plan are complete.

    Args:
        plan: The agent's Plan object containing tasks and subtasks.

    Returns:
        Tuple of (progress_message, is_complete):
        - progress_message: Description of remaining tasks or success message
        - is_complete: True if all tasks complete (or no plan), False otherwise
    """
    if not plan or not plan.tasks:
        return "No plan found or plan has no tasks.", True

    in_progress_tasks = []
    not_started_tasks = []

    for task in plan.tasks:
        # Build subtask lists for this task
        in_progress_subtasks = []
        not_started_subtasks = []

        for subtask in task.subtasks:
            subtask_info = {
                "id": subtask.id,
                "description": subtask.description,
                "status": subtask.status.value,
            }
            if subtask.status == TaskStatus.IN_PROGRESS:
                in_progress_subtasks.append(subtask_info)
            elif subtask.status == TaskStatus.NOT_STARTED:
                not_started_subtasks.append(subtask_info)

        # Build task info with nested subtasks
        task_info = {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
            "in_progress_subtasks": in_progress_subtasks,
            "not_started_subtasks": not_started_subtasks,
        }

        if task.status == TaskStatus.IN_PROGRESS:
            in_progress_tasks.append(task_info)
        elif task.status == TaskStatus.NOT_STARTED:
            not_started_tasks.append(task_info)

    if in_progress_tasks == [] and not_started_tasks == []:
        return "All tasks are complete, well done!", True

    # Build message with all incomplete tasks
    lines = ["Incomplete tasks remaining:"]

    for task in in_progress_tasks:
        lines.append(f"  - Task {task['id']}: {task['description']} (in progress)")
        for st in task["in_progress_subtasks"]:
            lines.append(f"      - {st['id']}: {st['description']} (in progress)")
        for st in task["not_started_subtasks"]:
            lines.append(f"      - {st['id']}: {st['description']} (not started)")

    for task in not_started_tasks:
        lines.append(f"  - Task {task['id']}: {task['description']} (not started)")
        for st in task["not_started_subtasks"]:
            lines.append(f"      - {st['id']}: {st['description']} (not started)")

    return "\n".join(lines), False
