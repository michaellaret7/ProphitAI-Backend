"""Task State Logger - Logs live plan state to task_state.yaml file.

This module provides functionality to log the current state of the agent's plan
to a YAML-formatted file, showing task progress and completion status.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.core.agentic_framework.base_agent.utils.models import Plan


def format_plan_state(plan: 'Plan') -> str:
    """Format plan into human-readable task list format.

    Args:
        plan: The agent's Plan object containing tasks and subtasks

    Returns:
        Formatted string representation of the plan state

    Example output:
        - Task 1: Portfolio Overview - Calculate key portfolio-level metrics [in progress]
          - Subtask 1a: Calculate portfolio returns metrics [complete]
            Work: Calculated returns using tool X. Found 46.1% annualized return...
          - Subtask 1b: Calculate portfolio beta vs SPY [not started]
    """
    if not plan or not plan.tasks:
        return "No plan available\n"

    lines = []

    for task in plan.tasks:
        # Format main task
        task_line = f"- Task {task.id}: {task.description} [{task.status.value}]"
        lines.append(task_line)

        # Add main task work summary if present
        if task.work_summary and task.work_summary.strip():
            lines.append(f"  Work: {task.work_summary.strip()}")

        # Format subtasks with indentation
        for subtask in task.subtasks:
            subtask_line = f"  - Subtask {subtask.id}: {subtask.description} [{subtask.status.value}]"
            lines.append(subtask_line)

            # Add subtask work summary if present
            if subtask.work_summary and subtask.work_summary.strip():
                lines.append(f"    Work: {subtask.work_summary.strip()}")

    return "\n".join(lines) + "\n"


def write_task_state_to_file(plan: 'Plan', output_dir: Optional[str] = None) -> None:
    """Write current plan state to task_state.yaml file.

    Args:
        plan: The agent's Plan object containing tasks and subtasks
        output_dir: Directory to write the file to (defaults to base_agent directory)
    """
    if not plan or not plan.tasks:
        return

    # Format the plan
    formatted_state = format_plan_state(plan)

    # Default to base_agent directory (same location as message history)
    if output_dir is None:
        base_agent_dir = Path(__file__).parent.parent
        output_path = base_agent_dir / "task_state.yaml"
    else:
        output_path = Path(output_dir) / "task_state.yaml"

    # Write to file
    output_path.write_text(formatted_state, encoding="utf-8")
