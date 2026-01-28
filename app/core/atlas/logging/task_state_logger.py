"""Task State Logger - Logs live plan state to task_state.yaml file."""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.core.atlas.models import Plan


def format_plan_state(plan: 'Plan') -> str:
    """Format plan into human-readable task list format.

    Args:
        plan: The agent's Plan object containing tasks and subtasks

    Returns:
        Formatted string representation of the plan state
    """
    if not plan or not plan.tasks:
        return "No plan available\n"

    lines = []

    for task in plan.tasks:
        task_line = f"- Task {task.id}: {task.description} [{task.status.value}]"
        lines.append(task_line)

        if task.work_summary and task.work_summary.strip():
            lines.append(f"  Work: {task.work_summary.strip()}")

        for subtask in task.subtasks:
            subtask_line = f"  - Subtask {subtask.id}: {subtask.description} [{subtask.status.value}]"
            lines.append(subtask_line)

            if subtask.work_summary and subtask.work_summary.strip():
                lines.append(f"    Work: {subtask.work_summary.strip()}")

    return "\n".join(lines) + "\n"


def write_task_state_to_file(plan: 'Plan', output_dir: Optional[str] = None) -> None:
    """Write current plan state to task_state.yaml file.

    Args:
        plan: The agent's Plan object containing tasks and subtasks
        output_dir: Directory to write the file to
    """
    if not plan or not plan.tasks:
        return

    formatted_state = format_plan_state(plan)

    if output_dir is None:
        base_dir = Path(__file__).parent.parent
        output_path = base_dir / "task_state.yaml"
    else:
        output_path = Path(output_dir) / "task_state.yaml"

    output_path.write_text(formatted_state, encoding="utf-8")
