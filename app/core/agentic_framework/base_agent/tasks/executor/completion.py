"""CompletionManager - Task completion checking and analytics.

Responsibilities:
- Validate task/subtask completion conditions
- Generate execution summaries
- Provide intelligent completion analysis
- Interface with CompletionValidator for boolean validation
"""

from typing import Tuple, Dict, Any, TYPE_CHECKING
from ..models import TaskStatus

if TYPE_CHECKING:
    from .executor_core import ExecutorCore


class CompletionManager:
    """Manages completion checking and execution analytics."""

    def __init__(self, core: 'ExecutorCore'):
        """Initialize the completion manager.

        Args:
            core: ExecutorCore instance for state access
        """
        self.core = core

    def check_task_completion_conditions(self) -> Tuple[bool, str]:
        """Check if current task should be marked as completed based on intelligent validation.

        Returns:
            Tuple of (should_complete, reason)
        """
        if not self.core.current_main_task:
            return False, "No current task"

        # Use TaskValidator for intelligent completion detection

        # First check current subtask if active
        if self.core.current_subtask:
            is_complete = self.core.task_validator.is_subtask_complete(
                self.core.current_subtask
            )

            if is_complete:
                return True, "SubTask completion detected"

        # Check main task completion
        is_complete = self.core.task_validator.is_main_task_complete(
            self.core.current_main_task
        )

        if is_complete:
            return True, "MainTask completion detected"
        else:
            return False, "MainTask in progress"

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the current execution state.

        Returns:
            Dictionary with execution summary including success field
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return {"success": True, "status": "no_plan"}

        completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        total_main = len(plan.tasks)

        summary = {
            "success": True,
            "plan_loaded": self.core.plan_loaded,
            "total_main_tasks": total_main,
            "completed_main_tasks": completed_main,
            "current_main_task": {
                "id": self.core.current_main_task.id,
                "description": self.core.current_main_task.description
            } if self.core.current_main_task else None,
            "current_subtask": {
                "id": self.core.current_subtask.id,
                "description": self.core.current_subtask.description
            } if self.core.current_subtask else None,
            "progress_percentage": int((completed_main / total_main) * 100) if total_main > 0 else 0
        }

        return summary

    def get_intelligent_completion_analysis(self) -> Dict[str, Any]:
        """Get detailed completion analysis using the TaskValidator.

        Returns:
            Dictionary with comprehensive completion analysis including success field
        """
        if not self.core.current_main_task:
            return {"success": True, "status": "no_current_task"}

        analysis = {
            "success": True,
            "current_main_task": {
                "id": self.core.current_main_task.id,
                "description": self.core.current_main_task.description,
                "status": self.core.current_main_task.status.value
            }
        }

        # Get main task completion status
        main_complete = self.core.task_validator.is_main_task_complete(
            self.core.current_main_task
        )

        analysis["main_task_analysis"] = {
            "is_complete": main_complete
        }

        # Get current subtask analysis if available
        if self.core.current_subtask:
            subtask_complete = self.core.task_validator.is_subtask_complete(
                self.core.current_subtask
            )

            analysis["current_subtask"] = {
                "id": self.core.current_subtask.id,
                "description": self.core.current_subtask.description,
                "completed": self.core.current_subtask.completed,
                "validation": {
                    "is_complete": subtask_complete
                }
            }

        # Get overall plan progress
        plan = self.core.task_store.get_current_structured_plan()
        if plan:
            completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
            total_main = len(plan.tasks)

            analysis["plan_progress"] = {
                "completed_main_tasks": completed_main,
                "total_main_tasks": total_main,
                "completion_percentage": round((completed_main / total_main) * 100, 1) if total_main > 0 else 0
            }

        return analysis
