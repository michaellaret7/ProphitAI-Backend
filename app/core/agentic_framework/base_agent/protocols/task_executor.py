"""TaskExecutor Protocol for task execution orchestration.

Enables dependency inversion: Agent depends on TaskExecutor protocol,
not concrete PlanExecutor implementation.
"""

from typing import Protocol, Optional, Dict, Any, Tuple
from ..tasks.models import TodoList, MainTask, SubTask


class TaskExecutor(Protocol):
    """Protocol for task execution orchestration.

    Any class implementing these methods satisfies this protocol,
    enabling dependency injection and testing with mocks.
    """

    def load_plan(self, plan: TodoList) -> bool:
        """Load a structured plan into the executor.

        Args:
            plan: The TodoList to execute

        Returns:
            True if plan loaded successfully, False otherwise
        """
        ...

    def get_current_task(self) -> Optional[MainTask]:
        """Get the currently active main task.

        Returns:
            The current MainTask, or None if no task is active
        """
        ...

    def get_current_subtask(self) -> Optional[SubTask]:
        """Get the currently active subtask.

        Returns:
            The current SubTask, or None if no subtask is active
        """
        ...

    def get_current_task_context(self) -> Dict[str, Any]:
        """Get context about the current task and execution state.

        Returns:
            Dictionary containing:
            - current_main_task: The active main task
            - current_subtask: The active subtask
            - completed_tasks: List of completed tasks
            - remaining_tasks: List of remaining tasks
            - progress_percentage: Overall progress
        """
        ...

    def advance_task_progression(self) -> Tuple[bool, str]:
        """Advance to the next task or subtask in the plan.

        Returns:
            Tuple of (success: bool, message: str)
            - success: True if advanced, False if plan complete or error
            - message: Description of what happened
        """
        ...

    def update_task_from_tool_result(self, tool_name: str, result: Any) -> bool:
        """Update task state based on a tool execution result.

        Args:
            tool_name: Name of the tool that was executed
            result: The result returned by the tool

        Returns:
            True if task updated successfully, False otherwise
        """
        ...