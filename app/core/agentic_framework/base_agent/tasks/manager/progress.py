"""Task progress tracking and reporting."""

from typing import Dict, Any, List
from ..models import TaskStatus
from .core import TaskManagerCore


class TaskProgressManager:
    """Manages task progress tracking and summary reporting.

    Responsibilities:
    - Calculate overall progress percentages
    - Provide progress summaries
    - Track failed tasks
    """

    def __init__(self, core: TaskManagerCore):
        """Initialize progress manager.

        Args:
            core: Core task manager for state access
        """
        self.core = core

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary of the structured plan.

        Returns:
            Dict containing progress metrics and percentages
        """
        if not self.core.structured_plan:
            return {"status": "no_plan"}

        total_main_tasks = len(self.core.structured_plan.tasks)
        completed_main_tasks = sum(
            1 for task in self.core.structured_plan.tasks
            if task.status == TaskStatus.COMPLETED
        )
        in_progress_main_tasks = sum(
            1 for task in self.core.structured_plan.tasks
            if task.status == TaskStatus.IN_PROGRESS
        )

        # Count subtasks
        total_subtasks = sum(len(task.subtasks) for task in self.core.structured_plan.tasks)
        completed_subtasks = sum(
            sum(1 for subtask in task.subtasks if subtask.completed)
            for task in self.core.structured_plan.tasks
        )

        # Calculate overall progress percentage
        if total_main_tasks > 0:
            main_progress = (completed_main_tasks / total_main_tasks) * 100
        else:
            main_progress = 0

        if total_subtasks > 0:
            subtask_progress = (completed_subtasks / total_subtasks) * 100
        else:
            subtask_progress = 0

        # Overall progress (weighted average)
        if total_subtasks > 0:
            overall_progress = (main_progress * 0.6) + (subtask_progress * 0.4)
        else:
            overall_progress = main_progress

        return {
            "total_main_tasks": total_main_tasks,
            "completed_main_tasks": completed_main_tasks,
            "in_progress_main_tasks": in_progress_main_tasks,
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
            "main_task_progress_percentage": round(main_progress, 1),
            "subtask_progress_percentage": round(subtask_progress, 1),
            "overall_progress_percentage": round(overall_progress, 1),
            "execution_history_entries": len(self.core.execution_history)
        }

    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """Get list of failed tasks with failure information.

        Returns:
            List of dicts containing failed task details
        """
        if not self.core.structured_plan:
            return []

        failed_tasks = []

        for task in self.core.structured_plan.tasks:
            if task.status == TaskStatus.FAILED:
                # Extract failure information from evidence
                failure_evidence = [ev for ev in task.completion_evidence if 'failed' in ev.lower()]

                failed_tasks.append({
                    'task_id': task.id,
                    'description': task.description,
                    'failure_evidence': failure_evidence,
                    'total_evidence': len(task.completion_evidence),
                    'observations': len(task.observations)
                })

        return failed_tasks

    def update_progress(self, iteration: int) -> None:
        """Update task progress marker (for iteration tracking).

        Args:
            iteration: Current iteration number
        """
        if self.core.verbose:
            print(f"Task progress update at iteration {iteration}")
